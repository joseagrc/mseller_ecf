# Install with frappe_docker

This repository is meant to be installed as a Frappe app, then included in a custom Docker image.

## Development

From the `frappe_docker` repository:

```bash
cp -R devcontainer-example .devcontainer
cp -R development/vscode-example development/.vscode
```

Open the folder in a devcontainer, then:

```bash
cd development
python installer.py --apps-json apps-example.json --site-name development.localhost
cd frappe-bench
bench get-app /workspace/mseller_ecf
bench --site development.localhost install-app mseller_ecf
bench --site development.localhost migrate
bench start
```

If your devcontainer mounts this repository at a different path, replace `/workspace/mseller_ecf` with the absolute path to the app folder.

## Production Image

Create an `apps.json` in the `frappe_docker` root:

```json
[
  {
    "url": "https://github.com/frappe/erpnext",
    "branch": "version-16"
  },
  {
    "url": "https://github.com/your-org/mseller_ecf",
    "branch": "main"
  }
]
```

Build:

```bash
docker build \
  --no-cache \
  --build-arg=FRAPPE_PATH=https://github.com/frappe/frappe \
  --build-arg=FRAPPE_BRANCH=version-16 \
  --secret=id=apps_json,src=apps.json \
  --tag=custom-erpnext-mseller:16 \
  --file=images/layered/Containerfile .
```

Deploy with:

```text
CUSTOM_IMAGE=custom-erpnext-mseller
CUSTOM_TAG=16
PULL_POLICY=missing
```

Then run `bench --site your-site install-app mseller_ecf` once per site, followed by `bench --site your-site migrate`.
