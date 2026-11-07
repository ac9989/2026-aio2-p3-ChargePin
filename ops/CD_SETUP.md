# ChargePin CD setup and one-time migration

This configuration is prepared on `feature/cd-deploy`. It does **not** deploy
to EC2 until the workflow is merged into the default branch (`main`), CI
succeeds on a push to `main`, and a reachable EC2 instance is configured.

## GitHub Actions variables

- `AWS_REGION=ap-northeast-2`
- `AWS_ROLE_ARN=arn:aws:iam::870853685597:role/ChargePinGitHubActionsRole`
- `EC2_INSTANCE_ID=<current instance ID>` (set before enabling deployments)

`GITHUB_TOKEN` publishes GHCR images in the existing CI workflow. AWS OIDC
authentication does not require static AWS access keys in GitHub Secrets.

The AWS role must trust `token.actions.githubusercontent.com` with audience
`sts.amazonaws.com` and subject
`repo:ac9989/2026-aio2-p3-ChargePin:ref:refs/heads/main`.

## Minimal SSM policy for the GitHub deployment role

Substitute the **actual target instance ID** before creating the policy.
Do not attach this policy to the EC2 instance role; attach it to
`ChargePinGitHubActionsRole`.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SendOnlyToChargePinInstance",
      "Effect": "Allow",
      "Action": "ssm:SendCommand",
      "Resource": [
        "arn:aws:ssm:ap-northeast-2::document/AWS-RunShellScript",
        "arn:aws:ec2:ap-northeast-2:870853685597:instance/REPLACE_INSTANCE_ID"
      ]
    },
    {
      "Sid": "ReadDeploymentCommandResult",
      "Effect": "Allow",
      "Action": "ssm:GetCommandInvocation",
      "Resource": "*"
    }
  ]
}
```

The IAM role on EC2 is separate. It still needs Systems Manager managed-instance
permissions. The instance must be running and online in Systems Manager, and
must be able to reach AWS SSM, GHCR and public GitHub raw content.

## One-time EC2 preparation

1. Start the **existing stopped** EC2 instance. Do not create a new one unless it
   was terminated. Confirm Fleet Manager shows it online.
2. Keep `/home/ubuntu/chargepin/.env` on the instance. It contains private
   service credentials and must not be committed or printed in CI logs.
3. Keep the running `chargepin-aws-postgres-1` and
   `chargepin-aws-redis-1` containers and their volumes untouched.
4. Check for the old manually created standalone `chargepin-frontend`
   container using `docker ps -a`. It binds port 8501; the new Compose
   frontend cannot start while that container owns the port. Back up the
   container configuration and stop/rename **only that frontend container**
   before the first controlled migration.
5. Confirm Nginx still proxies `127.0.0.1:8501`, the Docker Compose plugin
   works, and the required API keys are present in `.env`.
6. The deployment script runs `docker compose -f compose.prod.yml` under
   project `chargepin-aws`, matching the existing AWS containers. It updates
   only backend/frontend and intentionally never uses `--remove-orphans`.
7. A successful deployment requires health checks on backend `/healthz` and
   frontend `/_stcore/health`. Failure attempts rollback to the previously
   recorded successful commit SHA. On the **first** deployment there is no
   previous SHA and therefore no automatic rollback target.

## Activation

- The `ChargePin CD (AWS SSM)` workflow can be manually dispatched on the
  feature branch to validate deployment files **without contacting AWS**.
- After review, merge the CD changes into `main`.
- The deployment job triggers only after `ChargePin CI` succeeds on a
  `main` push. A failed CI build does not deploy.
- Configure `EC2_INSTANCE_ID` and the restrictive IAM policy **before** the
  first qualifying push after merge. Do not merge while the instance is stopped
  if you expect the first deployment to succeed.
- Review GitHub Actions and SSM command status after the first deployment.
  Verify the public page, authentication, Kakao map, provider calls and rollback
  behavior separately; a health endpoint alone does not prove application
  functionality.
