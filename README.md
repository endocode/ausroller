## Note

Clone this repository with `--recursive` to get the submodule example folder:
```
git clone --recursive https://github.com/endocode/ausroller
```

## Intro

Ausroller is a tool create, update and rollout Kubernetes resource yamls from a template.

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
    └── services
```
`templates` contains the deployment templates (Do'h!) and `rollout` contains the
 latest Kubernetes resource yamls which are already rolled out in a specific
namespace. Additional namespaces have to be deployed once and are in the
`namespace` directory. __This is the place where we store the productive
version numbers of all our components.__



## Initial configuration

Install dependencies:
```
sudo apt-get install git-buildpackage python-jinja2
```

or if you stuck on MacOS (or a Linux distro not shipping git-buildpackage):
```
pip install [--user] -r requirements.txt
```

Ausroller needs a config file to read the path to the "rollout" git repo from.
It looks for $HOME/.ausroller.ini by default but the path to the ausroller.ini
can be overwritten on command line: ``` ausroller [...] -c /etc/ausroller.ini```


Basic ausroller.ini looks like that:
```
[ausroller]
repopath = /home/<user>/git/k8s-resources
```

For easier usage you can link the ausroller.py from your cloned repository to
/usr/local/bin like that:
```
sudo ln -s $(pwd)/ausroller.py /usr/local/bin
```

__Ausroller expects a configured kubectl in the path.__
That means it calls  ```kubectl ``` to rollout or update the deployments on the
kubernetes cluster. Ensure that you talk with the right Kubernetes cluster
by running ```kubectl config view```.



## Usage

If everything prepared you can run the ausroller.py with the two mandatory parameters:

```
ausroller.py --namespace another-namespace --app your-app --version 47.11-1a
```

This command looks up for Kubernetes resource template files e.g. called
```your-app-deplyoment.tpl.yaml``` or ```your-app-configmap.tpl.yaml``` in the
directory ```templates/another-namespace/deplyoments/``` resp.
```templates/another-namespace/configmaps/``` in your configured repo-path. It
will fill in the version given by the command line parameter ```--version```,
add and commit the created Kubernetes resource files in the path
```rollout/another-namespace/deployments/your-app-deplyoment.yaml``` resp.
```rollout/another-namespace/configmaps/your-app-configmap.yaml```. Then it
checks if the Kubernetes resources already exist and updates it by running and
roll out the saved file by running ```kubectl apply -f
your-app-configmap.yaml``` resp. ```kubectl apply -f
your-app-deplyoment.yaml```. If a Kubernetes resource is unknown ausroller.py
creates it.

If you want more explanatory commit messages in the repository you can run ausroller.py with the optional parameter ```--message``` :
```
ausroller.py --namespace another-namespace --app my-app ---version 1.2.3-12a --message "Hotfix for foobar"
```


## Prepare and rollout a deployment

Create a normal deployment.yaml for your application but put the placeholder ` {{ app_version }} ` into the `image:` line instead of the Docker image tag. The placeholder will be substituted by the value of the `--version` cli parameter when running ausroller.py.

Save and commit the template into the directory `templates/deployments/` with the
filename  `<your-app>-deployment.tpl.yaml`

Now run `ausroller.py` like that
```
ausroller.py --namespace another-namespace --app your-app --version 47.11-1a --message "First rollout"
```

Ausroller will take the template you create (choosen by the value of parameter `--app`), replace the `{{ app_version}}` placeholder by the value of the parameter `--version`, add and commit the resulting file `your-app-deplyoment.yaml` to the directory `rollout/another-namespace/deployments/` and create the deployment in the Kubernetes cluster.

## Example

In the following example we use `ausroller` to rollout Nginx in a certain
version. This will create a deployment and a service from our templates in the
`example-resources/` folder. It also will produce a commit in that repository
with the according resource yamls.

After that we will upgrade the Nginx to a newer version.


### Prerequisites

* `kubectl` has to be configured to a cluster

### Steps

Make sure that we have the namespace we want to rollout to:
```
kubectl apply -f example-resources/namespaces/another-namespace.yaml
```

Rollout Nginx. This will produce a commit in `example-resources/`:
```
./ausroller.py --config example-resources/ausroller.ini --namespace another-namespace --app nginx --version 1.10.2-alpine
```

Check what happened:
```
kubectl --namespace=another-namespace get svc,deployment,pods
```

Upgrade Nginx:

```
./ausroller.py --config example-resources/ausroller.ini --namespace another-namespace --app nginx --version 1.11.5-alpine
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
