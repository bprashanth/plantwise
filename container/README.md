# Plantwise baseline code 

## How this sub-directory was created 

This directory contains files rsynced from the plantwise production container
```
gcloud auth login (as plantwise30@gmail.com)
docker pull gcr.io/plantwise30/species-api@sha256:7202bfc182fdd37f13006137f9d5c476a88cbd8a02f6d2da3a6a8bc449103261 
docker tag gcr.io/plantwise30/species-api@sha256:7202bfc182fdd37f13006137f9d5c476a88cbd8a02f6d2da3a6a8bc449103261 plantwise:v0
```

## Where is the code now? 

The local container image is currently tagged as:

```bash
plantwise:v0
```

You can discover the AWS account ID currently active in your AWS CLI with:

```bash
aws sts get-caller-identity
```

The `Account` field in that output is the number to use in the ECR image name.

To publish it to AWS ECR, use the helper script in this directory:

```bash
cd PlantWise_v0/container
./push.sh <AWS_ACCOUNT_ID> <AWS_REGION> [ECR_REPOSITORY_NAME]
```

Example:

```bash
cd PlantWise_v0/container
./push.sh 123456789012 ap-south-1 plantwise
```

This pushes the local image `plantwise:v0` to:

```bash
123456789012.dkr.ecr.ap-south-1.amazonaws.com/plantwise:v0
```

You can pull the same image with:

```bash
docker pull 024848460644.dkr.ecr.ap-south-1.amazonaws.com/plantwise:v0
```

To run the image locally:

```bash
docker run --rm -p 8080:8080 plantwise:v0
```

This starts the FastAPI app on port `8080`.

You can verify that it is up with:

```bash
curl http://127.0.0.1:8080/
```

You can test the species suggestion endpoint with:

```bash
curl -X POST http://127.0.0.1:8080/api/get-results \
  -H 'Content-Type: application/json' \
  -d '{"latitude":10.46675,"longitude":76.8295,"minProbability":50}'
```

Expected response shape:

```json
[
  {
    "species": "Some_species_name",
    "probability": 78,
    "auc": 0.93
  }
]
```

You can also open the generated FastAPI docs at:

```bash
http://127.0.0.1:8080/docs
```



# Connecting K3s to AWS ECR

Follow these steps on your K3s nodes to automatically authenticate and pull private images from AWS ECR without using manual Kubernetes secrets.

## 1. Install the ECR Credential Provider
Download and set up the AWS credential provider binary on your node.

```bash
wget https://github.com
chmod +x ecr-credential-provider-linux-amd64
sudo mv ecr-credential-provider-linux-amd64 /usr/local/bin/ecr-credential-provider
```

## 2. Create the Configuration File
Create the required directory and configuration file to tell Kubernetes which registry patterns to match.

```bash
sudo mkdir -p /etc/kubernetes
sudo tee /etc/kubernetes/ecr-credential-provider.json > /dev/null <<EOF
{
  "providers": [
    {
      "name": "ecr-credential-provider",
      "matchImages": [
        "*.dkr.ecr.*.amazonaws.com",
        "*.dkr.ecr.*.amazonaws.com.cn"
      ],
      "defaultCacheDuration": "1h"
    }
  ]
}
EOF
```

## 3. Assign IAM Permissions
Ensure your node has access to read from ECR.
* **On AWS EC2:** Attach an IAM role to the instance with the `AmazonEC2ContainerRegistryReadOnly` policy.
* **Outside AWS:** Configure your AWS credentials file at `~/.aws/credentials` or set environment variables for the user running K3s.

## 4. Configure and Restart K3s
Update your K3s configuration to point to the credential provider binary and config file.

Edit or create `/etc/rancher/k3s/config.yaml`:

```yaml
kubelet-arg:
  - "image-credential-provider-config=/etc/kubernetes/ecr-credential-provider.json"
  - "image-credential-provider-bin-dir=/usr/local/bin"
```

Restart the K3s service to apply the flags:

```bash
sudo systemctl restart k3s
```

## 5. Deploy without imagePullSecrets
You can now deploy workloads without defining any `imagePullSecrets` in your manifest files.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: test-ecr-app
spec:
  containers:
  - name: my-app
    image: <AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>://
```
