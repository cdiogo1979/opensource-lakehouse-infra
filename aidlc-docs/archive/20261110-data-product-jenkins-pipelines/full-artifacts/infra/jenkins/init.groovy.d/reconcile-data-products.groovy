// Apply the data product folders and jobs, then delete the ones that left the product files.
//
// Both inputs are rendered by infra/products/render_jenkins.py. This runs as an init
// hook, after Jenkins has loaded its jobs: a Job DSL script in CasC runs before that,
// and the folders it creates would be dropped until the next restart.
//  1. /run/lakehouse/jenkins-jobs.groovy (Job DSL) creates or updates every folder,
//     its permissions, and its <name>_ci and <name>_cd jobs.
//  2. /run/lakehouse/jenkins-products.json ({"<name>": ["<name>_ci", "<name>_cd"]})
//     drives deletion, which touches only top-level folders whose description holds
//     the marker: a folder missing from the state is deleted with everything in it;
//     in a listed folder, an unlisted <name>_ci or <name>_cd job is deleted. Other
//     items, including jobs owners create in their folder, are kept.
import com.cloudbees.hudson.plugins.folder.Folder
import groovy.json.JsonSlurper
import java.util.logging.Level
import java.util.logging.Logger
import javaposse.jobdsl.dsl.DslScriptLoader
import javaposse.jobdsl.plugin.JenkinsJobManagement
import jenkins.model.Jenkins

def log = Logger.getLogger('lakehouse.reconcile-data-products')
def marker = 'Managed by the lakehouse data product files.'
def jobsFile = new File('/run/lakehouse/jenkins-jobs.groovy')
def stateFile = new File('/run/lakehouse/jenkins-products.json')

try {
  def management = new JenkinsJobManagement(System.out, [:], new File(Jenkins.get().rootDir, 'jobs'))
  def generated = new DslScriptLoader(management).runScript(jobsFile.text)
  log.info("Applied data product folders and jobs (${generated.jobs.size()} items).")
} catch (Exception error) {
  log.log(Level.SEVERE, 'Data product folders and jobs not applied; nothing deleted.', error)
  return
}

def desired = null
try {
  desired = new JsonSlurper().parse(stateFile)
} catch (Exception error) {
  log.warning("Data product state not readable (${error.class.simpleName}); nothing deleted.")
  return
}
if (!(desired instanceof Map) || desired.isEmpty()) {
  log.warning('Data product state is empty or not an object; nothing deleted.')
  return
}

Jenkins.get().getItems(Folder).each { folder ->
  if (!(folder.description ?: '').contains(marker)) {
    return
  }
  if (!desired.containsKey(folder.name)) {
    folder.delete()
    log.info("Deleted folder ${folder.name} (data product removed).")
    return
  }
  def jobs = desired[folder.name] instanceof List ? desired[folder.name] : []
  ['_ci', '_cd'].collect { folder.name + it }.findAll { !(it in jobs) }.each { name ->
    def job = folder.getItem(name)
    if (job != null) {
      job.delete()
      log.info("Deleted ${folder.name}/${name} (no longer in the product file).")
    }
  }
}
