package local.lakehouse.spark.auth;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.KeyStore;
import java.time.Duration;
import java.time.Instant;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import javax.net.ssl.SSLContext;
import javax.net.ssl.TrustManagerFactory;
import org.apache.iceberg.rest.HTTPHeaders;
import org.apache.iceberg.rest.HTTPRequest;
import org.apache.iceberg.rest.ImmutableHTTPRequest;
import org.apache.iceberg.rest.RESTClient;
import org.apache.iceberg.rest.auth.AuthManager;
import org.apache.iceberg.rest.auth.AuthSession;

/** Shared Iceberg REST authenticator for Hub user and Airflow writer broker sessions. */
public final class LakehouseTokenAuthManager implements AuthManager {
  private static final ObjectMapper JSON = new ObjectMapper();
  private static final long REFRESH_WINDOW_SECONDS = 120;
  private static final long MIN_RETRY_REMAINING_SECONDS = 60;
  private static final int REQUEST_TIMEOUT_SECONDS = 5;
  private static final int MAX_ATTEMPTS = 3;

  private final String provider;
  private final String brokerUrl;
  private final String brokerCa;
  private final String initialToken;
  private final String hubApiToken;
  private final String runHandle;
  private final String runCapability;
  private final HttpClient http;
  private final Object tokenLock = new Object();
  private volatile String accessToken;
  private volatile long expiresAt;

  /** Constructor shape required by Iceberg AuthManagers reflection. */
  public LakehouseTokenAuthManager(String ignored) {
    this.provider = requiredEnv("LAKEHOUSE_TOKEN_PROVIDER");
    if (!provider.equals("jupyter") && !provider.equals("airflow")) {
      throw new IllegalStateException("Unsupported Lakehouse token provider.");
    }
    this.brokerUrl = requiredEnv("LAKEHOUSE_TOKEN_BROKER_URL");
    this.brokerCa = requiredEnv("LAKEHOUSE_TOKEN_BROKER_CA");
    this.initialToken = requiredEnv("LAKEHOUSE_INITIAL_ACCESS_TOKEN");
    this.hubApiToken = provider.equals("jupyter") ? requiredEnv("JUPYTERHUB_API_TOKEN") : null;
    this.runHandle = provider.equals("airflow") ? requiredEnv("LAKEHOUSE_RUN_HANDLE") : null;
    this.runCapability = provider.equals("airflow") ? requiredEnv("LAKEHOUSE_RUN_CAPABILITY") : null;
    if (!brokerUrl.startsWith("https://") || !Files.isRegularFile(Path.of(brokerCa))) {
      throw new IllegalStateException("A trusted HTTPS token broker is required.");
    }
    this.accessToken = initialToken;
    this.expiresAt = expiryFromJwt(initialToken);
    this.http = HttpClient.newBuilder()
        .connectTimeout(Duration.ofSeconds(REQUEST_TIMEOUT_SECONDS))
        .sslContext(trustContext(Path.of(brokerCa)))
        .followRedirects(HttpClient.Redirect.NEVER)
        .build();
  }

  @Override
  public AuthSession catalogSession(RESTClient sharedClient, Map<String, String> properties) {
    return new TokenSession();
  }

  @Override
  public void close() {
    // HttpClient owns no closeable resources on the supported Java 17 runtime.
  }

  private final class TokenSession implements AuthSession {
    @Override
    public HTTPRequest authenticate(HTTPRequest request) {
      String token = currentToken();
      Map<String, String> headers = new LinkedHashMap<>();
      request.headers().entries().forEach(header -> headers.put(header.name(), header.value()));
      headers.keySet().removeIf(name -> name.equalsIgnoreCase("Authorization"));
      headers.put("Authorization", "Bearer " + token);
      return ImmutableHTTPRequest.builder().from(request)
          .headers(HTTPHeaders.of(headers)).build();
    }

    @Override
    public void close() {}
  }

  private String currentToken() {
    if (expiresAt - Instant.now().getEpochSecond() > REFRESH_WINDOW_SECONDS) return accessToken;
    synchronized (tokenLock) {
      if (expiresAt - Instant.now().getEpochSecond() > REFRESH_WINDOW_SECONDS) return accessToken;
      return renewWithRetry();
    }
  }

  private String renewWithRetry() {
    IOException lastFailure = null;
    for (int attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
      if (attempt > 0) {
        if (expiresAt - Instant.now().getEpochSecond() <= MIN_RETRY_REMAINING_SECONDS) break;
        try {
          TimeUnit.SECONDS.sleep(attempt); // one second, then two seconds
        } catch (InterruptedException interrupted) {
          Thread.currentThread().interrupt();
          throw new IllegalStateException("Token renewal was interrupted.");
        }
      }
      try {
        JsonNode response = requestRenewal();
        JsonNode value = response.get("access_token");
        if (value == null || !value.isTextual()) throw new IOException("Invalid broker response.");
        String candidate = value.textValue();
        long candidateExpiry = expiryFromJwt(candidate);
        long responseExpiry = parseResponseExpiry(response.get("expires_at"));
        if (candidateExpiry != responseExpiry || candidateExpiry <= Instant.now().getEpochSecond() + MIN_RETRY_REMAINING_SECONDS) {
          throw new IOException("Invalid broker token expiry.");
        }
        // Publish both fields together under tokenLock so request threads see one identity/expiry pair.
        this.accessToken = candidate;
        this.expiresAt = candidateExpiry;
        return candidate;
      } catch (IOException | InterruptedException error) {
        if (error instanceof InterruptedException) {
          Thread.currentThread().interrupt();
          throw new IllegalStateException("Token renewal was interrupted.");
        }
        lastFailure = (IOException) error;
      }
    }
    // Do not continue with a token that will expire during a retry delay.
    if (expiresAt - Instant.now().getEpochSecond() <= MIN_RETRY_REMAINING_SECONDS) {
      throw new IllegalStateException("Token renewal failed before the active token safety window.");
    }
    if (lastFailure != null) throw new IllegalStateException("Token renewal failed; broker details were suppressed.");
    throw new IllegalStateException("Token renewal stopped before the active token safety window.");
  }

  private JsonNode requestRenewal() throws IOException, InterruptedException {
    String endpoint;
    String bearer;
    String body;
    if (provider.equals("jupyter")) {
      endpoint = brokerUrl.endsWith("/api/v1/token") ? brokerUrl : brokerUrl + "/api/v1/token";
      bearer = hubApiToken;
      body = "{}";
    } else {
      endpoint = brokerUrl.endsWith("/") ? brokerUrl + "v1/runs/token" : brokerUrl + "/v1/runs/token";
      bearer = runCapability;
      body = JSON.writeValueAsString(Map.of("run_handle", runHandle));
    }
    HttpRequest request = HttpRequest.newBuilder(URI.create(endpoint))
        .timeout(Duration.ofSeconds(REQUEST_TIMEOUT_SECONDS))
        .header("Authorization", "Bearer " + bearer)
        .header("Content-Type", "application/json")
        .header("Accept", "application/json")
        .POST(HttpRequest.BodyPublishers.ofString(body))
        .build();
    HttpResponse<String> response = http.send(request, HttpResponse.BodyHandlers.ofString());
    if (response.statusCode() != 200 || response.body().length() > 8192) {
      throw new IOException("Token broker rejected the renewal.");
    }
    JsonNode parsed = JSON.readTree(response.body());
    if (parsed == null || !parsed.isObject()) throw new IOException("Invalid broker response.");
    return parsed;
  }

  private static long parseResponseExpiry(JsonNode node) throws IOException {
    if (node == null) throw new IOException("Missing token expiry.");
    if (node.isIntegralNumber()) return node.longValue();
    if (node.isTextual()) {
      try { return Instant.parse(node.textValue()).getEpochSecond(); }
      catch (RuntimeException error) { throw new IOException("Invalid token expiry."); }
    }
    throw new IOException("Invalid token expiry.");
  }

  private static long expiryFromJwt(String token) {
    try {
      String[] parts = token.split("\\.");
      if (parts.length != 3 || token.length() > 16384) throw new IllegalArgumentException();
      JsonNode payload = JSON.readTree(Base64.getUrlDecoder().decode(parts[1]));
      JsonNode expiry = payload.get("exp");
      if (expiry == null || !expiry.isIntegralNumber()) throw new IllegalArgumentException();
      return expiry.longValue();
    } catch (Exception error) {
      throw new IllegalStateException("The initial token is invalid.");
    }
  }

  private static SSLContext trustContext(Path caPath) {
    try {
      KeyStore trust = KeyStore.getInstance(KeyStore.getDefaultType());
      trust.load(null, null);
      try (var input = Files.newInputStream(caPath)) {
        var factory = java.security.cert.CertificateFactory.getInstance("X.509");
        trust.setCertificateEntry("lakehouse-token-broker", factory.generateCertificate(input));
      }
      TrustManagerFactory managers = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm());
      managers.init(trust);
      SSLContext context = SSLContext.getInstance("TLS");
      context.init(null, managers.getTrustManagers(), null);
      return context;
    } catch (Exception error) {
      throw new IllegalStateException("The token broker CA certificate is invalid.");
    }
  }

  private static String requiredEnv(String name) {
    String value = System.getenv(name);
    if (value == null || value.isBlank()) throw new IllegalStateException("Required token provider configuration is missing.");
    return value;
  }
}
