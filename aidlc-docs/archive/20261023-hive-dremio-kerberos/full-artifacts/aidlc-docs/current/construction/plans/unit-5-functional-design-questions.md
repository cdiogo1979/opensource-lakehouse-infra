# Unit 5 Functional Design Questions

Please answer each item with a letter after `[Answer]:`. These decisions shape the JupyterHub integration and per-user Spark session behavior.

## Question 1
How should the existing sibling `jupyter-platform/` deployment be integrated with this PoC?

A) Bring its Hub and single-user image configuration into `hive-dremio-rustfs` and add the required service/network wiring to the existing Compose project.

B) Keep a separate Jupyter Compose project and connect it to this PoC's existing Docker network.

X) Other (please describe after `[Answer]:` below)

[Answer]:A

## Question 2
Where should each user's Spark session execute?

A) Run Spark locally inside that user's isolated single-user notebook container, matching the existing single-user image approach.

B) Connect each notebook session to a shared Spark service or cluster.

X) Other (please describe after `[Answer]:` below)

[Answer]:A

## Question 3
What should the development identity mapping allow in JupyterHub?

A) DummyAuthenticator accepts the usernames `user_a`, `user_b`, and `admin`; each username maps only to its matching provisioned identity, and `admin` is marked as a Hub administrator.

B) Allow only `user_a` and `user_b` in Hub; administer Hub through a separate operator mechanism without an `admin` notebook session.

X) Other (please describe after `[Answer]:` below)

[Answer]:A

## Question 4
How should a notebook session receive its user's credentials?

A) Mount that user's keytab read-only and inject only that user's distinct RustFS credentials into their isolated container; initialize a private Kerberos ticket cache when the session starts.

B) Mount a per-user credential file read-only and have session startup read it to initialize both Kerberos and RustFS settings.

X) Other (please describe after `[Answer]:` below)

[Answer]:A

## Question 5
How should notebook files persist when a user's container stops or is recreated?

A) Preserve a separate per-user work volume; do not share writable notebooks between users.

B) Keep notebook work ephemeral and provide only the existing shared notebooks mount as read-only reference material.

C) Preserve per-user work volumes and also provide the existing shared notebooks directory as writable shared material.

X) Other (please describe after `[Answer]:` below)

[Answer]: A
