### Category: DevOps and CI/CD

Tasks involving CI/CD pipeline implementation, container orchestration, infrastructure as code, deployment automation, and DevOps tooling.

**The examples below are for inspiration only. Be creative and design your own unique task!**

**Task Pattern Ideas**:
- Build CI/CD pipeline migration tools (Jenkins to GitHub Actions, CircleCI to GitLab)
- Implement pipeline orchestrators with DAG scheduling and dependency resolution
- Create container image layer analysis and build cache optimizers
- Build deployment rollout orchestrators with canary/blue-green strategies
- Implement infrastructure drift detection tools
- Create GitOps reconciliation engines
- Build artifact registry management systems
- Implement pipeline secret scanning and rotation tools
- Create environment promotion workflows with approval gates
- Build multi-environment deployment manifest generators
- Implement CI pipeline consolidation for monorepos
- Create build artifact provenance chain validators
- Build deployment health check orchestrators
- Implement pipeline resource optimization (caching, parallelization)
- Create release versioning automation tools (semantic-release)

**Skills & Tools** (tag suggestions for your task):
- Core: `cicd`, `devops`, `deployment`, `automation`, `infrastructure`
- Platforms: `github-actions`, `gitlab-ci`, `jenkins`, `circleci`, `argocd`
- Containers: `docker`, `kubernetes`, `helm`, `podman`
- IaC: `terraform`, `ansible`, `pulumi`, `cloudformation`
- Concepts: `gitops`, `immutable-infrastructure`, `canary`, `blue-green`

**Possible Input Data** (be creative with environment files!):
- Pipeline configuration files (YAML, Jenkinsfile, .circleci/config.yml)
- Kubernetes manifests and Helm charts
- Terraform/Ansible configurations
- Docker/container images and Dockerfiles
- Environment variable definitions
- Secret management configurations
- Deployment history and rollback data
- Build logs and timing metrics
- Artifact metadata and checksums
- Service mesh configurations

**Verification Approaches**:
- Pipeline executes successfully end-to-end
- Migrated pipeline produces identical artifacts
- Deployment completes without downtime
- Rollback works correctly
- Secrets not exposed in logs or artifacts
- Build cache improves performance
- Drift detection identifies all changes
- Health checks pass post-deployment
- Resource constraints respected
- Approval gates enforced correctly

**Remember**: DevOps tasks should include realistic constraints (network policies, resource limits, secrets management) and test understanding of deployment strategies and failure recovery!
