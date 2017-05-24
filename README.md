[![Build Status](https://travis-ci.org/endocode/ausroller.svg?branch=master)](https://travis-ci.org/endocode/ausroller)

## Note

Clone this repository with `--recursive` to get the submodule example folder:
```
git clone --recursive https://github.com/endocode/ausroller
```

If your Kubernetes API server uses a self-signed certificate, you have to configure your `kubectl` properly.
Either set the certificate authority:
```
kubectl config set-cluster <NAME> --certificate-authority=/path/to/ca.crt
```
or just skip crtificate verification:
```
kubectl config set-cluster <NAME> --insecure-skip-tls-verify=true
```

## Intro

Ausroller is a tool to create, update and rollout Kubernetes resource yamls from a template.

Our central configuration repository ``k8s-resources`` contains the
directories ``templates``, ``rollout``, ``namespaces`` and ``secrets``.

```
.
├── namespaces
│   └── another-namespace.yaml
├── rollout
│   ├── default
│   │   ├── configmaps
│   │   ├── deployments
│   │   ├── pods
│   │   ├── replicationcontrollers
│   │   ├── secrets
│   │   └── services
│   ├── kube-system
│   │   ├── deployments
│   │   ├── replicationcontrollers
│   │   ├── secrets
│   │   └── services
│   └── another-namespace
│       ├── configmaps
│       ├── deployments
│       ├── pods
│       ├── replicationcontrollers
│       ├── secrets
│       └── services
├── secrets
│   ├── default
│   │   └── secret_vars.json
│   ├── kube-system
│   │   └── secret_vars.json
│   └── another-namespace
│       └── secret_vars.json
└── templates
    ├── configmaps
    ├── deployments
    ├── pods
    ├── replicationcontrollers
    ├── secrets
    └── services
```
`templates` contains the deployment templates (Do'h!) and `rollout` contains the
 latest Kubernetes resource yamls which are already rolled out in a specific
namespace. Additional namespaces have to be deployed once and are in the
`namespace` directory. __This is the place where we store the productive
version numbers of all our components.__



## Initial configuration

### Install ausroller

At the moment ausroller is not compatible with Python3. If you are using a distribution that defaults to Python3 e.g. Arch Linux you should use a virtual environment as follows:
```
virtualenv -p python2 ausroller
source ausroller/bin/activate
```

#### Install ausroller using pip:
```
pip install git+https://github.com/endocode/ausroller@0.3.1
```

Remove the version number to install the latest version from the master branch.

Ausroller needs a configuration file to read the path to the "rollout" git repository from.
It looks for $HOME/.ausroller.ini by default but the path to the ausroller.ini
can be overwritten on command line: ``` ausroller [...] -c /etc/ausroller.ini```


Basic ausroller.ini looks like that:
```
[ausroller]
<kubectlpath = /opt/k8s/bin/kubectl>

[another-context]
repopath = /home/<user>/git/k8s-resources
```
If you omit the `kubectlpath` option ausroller will try to find `kubectl` on your `$PATH` to rollout your resources.

You must specify the path to the repository to use for each Kubernetes context you want to use.

List configured Kubernetes contexts:
`kubectl config get-contexts`

## Usage

If everything is prepared you can run the ausroller with the four mandatory parameters:

```
ausroller --namespace another-namespace --context another-context --app your-app --ver 47.11-1a
```

This command looks up for Kubernetes resource template files e.g. called
```your-app-deployment.tpl.yaml``` or ```your-app-configmap.tpl.yaml``` in the
directory ```templates/another-namespace/deployments/``` resp.
```templates/another-namespace/configmaps/``` in your configured repo-path. It
will fill in the version given by the command line parameter ```--ver```,
add and commit the created Kubernetes resource files in the path
```rollout/another-namespace/deployments/your-app-deployment.yaml``` resp.
```rollout/another-namespace/configmaps/your-app-configmap.yaml```. Then it
checks if the Kubernetes resources already exist and updates it by running and
roll out the saved file by running ```kubectl apply -f
your-app-configmap.yaml``` resp. ```kubectl apply -f
your-app-deplyoment.yaml```. If a Kubernetes resource is unknown ausroller
creates it.

If you want more explanatory commit messages in the repository you can run ausroller with the optional parameter ```--message``` :
```
ausroller --namespace another-namespace --context another-context --app my-app --ver 1.2.3-12a --message "Hotfix for foobar"
```


## Prepare and rollout a deployment

Create a normal deployment.yaml for your application but put the placeholder ` {{ app_version }} ` into the `image:` line instead of the Docker image tag. The placeholder will be substituted by the value of the `--ver` cli parameter when running ausroller.

Save and commit the template into the directory `templates/deployments/` with the
filename  `<your-app>-deployment.tpl.yaml`

Now run `ausroller` like that
```
ausroller --namespace another-namespace --context another-context --app your-app --ver 47.11-1a --message "First rollout"
```

Ausroller will take the template you create (choosen by the value of parameter `--app`), replace the `{{ app_version}}` placeholder by the value of the parameter `--ver`, add and commit the resulting file `your-app-deplyoment.yaml` to the directory `rollout/another-namespace/deployments/` and create the deployment in the Kubernetes cluster.

## Example

In the following example we use `ausroller` to rollout Nginx in a certain
version. This will create a deployment and a service from our templates in the
`example-resources/` folder. It also will produce a commit in that repository
with the according resource yamls.

After that we will upgrade the Nginx to a newer version.


### Prerequisites

* `kubectl` has to be configured to a cluster

For a quick-start use `minikube` to setup a local cluster.
For example bring up a cluster in a kvm virtual machine:
```
minikube --vm-driver=kvm start
```
### Steps

Make sure that we have the namespace we want to rollout to:
```
kubectl apply -f example-resources/namespaces/another-namespace.yaml
```

Rollout Nginx. This will produce a commit in `example-resources/`:
```
ausroller --config example-resources/ausroller.ini --namespace another-namespace --context minikube --app nginx --ver 1.10.2-alpine
```

Check what happened:
```
kubectl --namespace=another-namespace get svc,deployment,pods
```

Upgrade Nginx:

```
ausroller --config example-resources/ausroller.ini --namespace another-namespace --context minikube --app nginx --ver 1.11.5-alpine
```

Again check what happened:
```
kubectl --namespace=another-namespace get svc,deployment,pods
```

### Cleanup

Delete Kubernetes resources:
```
kubectl --namespace=another-namespace delete svc nginx-service
```

```
kubectl --namespace=another-namespace delete deployment nginx-deployment
```

```
kubectl delete namespace another-namespace
```

Remove the commits produced by `ausroller`:
```
( cd example-resources/ && git reset --hard HEAD~2 )
```

## Development

When implementing new features place some unit tests in the tests directory.

Running the unit tests:

```
python -m unittest discover -v tests
```
