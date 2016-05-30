## Intro

Ausroller is a tool create, update and rollout deployment.yamls from a template.

Our central configuration repository ``k8s-resources`` contains the
directories ``templates`` and ``rollout``.

```
├── rollout
│   └── deployments
│       └── did-microservice-deployment.yaml
└── templates
    └── deployments
        └── did-microservice-deployment.tpl.yaml
```
`templates` contains the deployment templates (Do'h!) and `rollout` contains the
 latest deployments.yamls which are already rolled out. __This is the place
 where we store the productive version numbers of all our components.__



## Initial configuration

Install dependencies:
```
sudo apt-get install git-buildpackage python-jinja2
```

Or if you stuck on MacOS:
```
git clone git://honk.sigxcpu.org/git/git-buildpackage.git
cd git-buildpackage.git
python setup.py install  [ --user ]
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
ausroller.py --app your-app --version 47.11-1a
```

This command looks up for a deployment template file called
```your-app-deplyoment.tpl.yaml``` in the directory ```templates/deployments/```
in your configured repo-path. It will fill in the version given by the command
line parameter ```--version```, add and commit the created deployment file in
the path ```rollout/deployments/your-app-deplyoment.yaml```. Then it checks if
the deployment already exists and updates it by running  and roll out the saved
file by running ```kubectl apply -f your-app-deplyoment.yaml```. If the
deployment is unknown to Kubernetes ausroller.py creates a new deployment by
running ```kubectl create -f your-app-deplyoment.yaml```.

If you want more explanatory commit messages in the repository you can run ausroller.py with the optional parameter ```--message``` :
```
ausroller.py --app my-app ---version 1.2.3-12a --message "Hotfix for foobar"
```


## Prepare and rollout a deployment

Create a normal deployment.yaml for your application but put the placeholder ` {{ app_version }} ` into the `image:` line instead of the Docker image tag. The placeholder will be substituted by the value of the `--version` cli parameter when running ausroller.py.

Save and commit the template into the directory `templates/deployments/` with the
filename  `<your-app>-deployment.tpl.yaml`

Now run `ausroller.py` like that
```
ausroller.py --app your-app --version 47.11-1a --message "First rollout"
```

Ausroller will take the template you create (choosen by the value of parameter `--app`), replace the `{{ app_version}}` placeholder by the value of the parameter `--version`, add and commit the resulting file `your-app-deplyoment.yaml` to the directory `rollout/deployments/` and create the deployment in the Kubernetes cluster.
