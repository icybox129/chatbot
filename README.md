# **AI Terraform Chatbot Documentation**

## **Overview**
The AI Terraform Chatbot is an intelligent, developer-friendly application designed to provide real-time assistance in creating and troubleshooting AWS resources using Terraform. It leverages an embedded knowledge base, AI-powered query processing, and is hosted in a highly scalable and secure AWS environment.

---

## **Features**
- **AI Assistance**: Provides up-to-date Terraform information to assist developers with AWS resource creation.
- **Preprocessing Pipeline**: Converts markdown documentation into ChromaDB vector indexes for efficient query handling.
- **Web Interface**: Intuitive frontend with a Flask-based backend to handle user queries.
- **Infrastructure-as-Code (IaC)**: Uses Terraform to provision and manage the entire AWS infrastructure.
- **Scalable Hosting**: Deployed via ECS Fargate for container orchestration.

---

## **Architecture**
### **1. Application Architecture**
- **Frontend**: HTML, CSS, and JavaScript for a responsive user interface.
- **Backend**: Flask application that handles:
  - User queries
  - AI processing via OpenAI APIs
  - Session and state management
- **Preprocessing**: Python scripts to:
  - Chunk and vectorise markdown documents
  - Store processed data in ChromaDB

### **2. Infrastructure**
- **AWS ECS Fargate**: Runs containerised frontend and backend services.
- **ALB (Application Load Balancer)**: Distributes traffic between ECS tasks.
- **CloudWatch**: Monitors metrics such as CPU and memory utilisation, ALB requests, and custom alerts.

---

## **Setup Instructions**
### **Prerequisites**
- Python 3.10 or higher
- Node.js 20.x
- Docker
- AWS CLI
- Terraform CLI
- OpenAI API key
- Snyk API token (optional for security scans)

### **Step 1: Clone the Repository**
```bash
git clone <repository-url>
cd <repository-directory>
```

### **Step 2: Install Dependencies**
#### Python:
```bash
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```
#### JavaScript:
```bash
npm install
```

### **Step 3: Set Up Environment Variables**
Create a `.env` file and include:
```dotenv
OPENAI_API_KEY=<your-api-key>
AWS_ACCESS_KEY_ID=<your-aws-access-key>
AWS_SECRET_ACCESS_KEY=<your-aws-secret-key>
```

### **Step 4: Run Locally**
- **Preprocessing**:
  ```bash
  python preprocessing.py
  ```
- **Backend**:
  ```bash
  flask run
  ```
- **Frontend**:
  Serve static files using any HTTP server or the provided Docker setup.

---

## **Deployment**
### **Automated Deployment via GitHub Actions**
1. Push changes to the `main` branch.
2. The CI/CD pipeline:
   - Runs unit tests for Python and JavaScript.
   - Scans for vulnerabilities using Snyk.
   - Deploys the infrastructure using Terraform.
   - Builds and pushes Docker images to Amazon ECR.
   - Updates the ECS Fargate tasks with the latest images.

### **Manual Deployment**
1. Use Terraform to initialise and apply the infrastructure:
   ```bash
   cd infrastructure/environment/dev
   terraform init
   terraform apply
   ```
2. Build and push Docker images:
   ```bash
   docker build -t backend:latest -f Dockerfile.backend .
   docker build -t frontend:latest -f Dockerfile.frontend .
   ```
3. Update ECS services with the new images.

---

## **Monitoring**
- **CloudWatch Dashboard**:
  - **Metrics**: ECS CPU/Memory utilisation, ALB request counts, 4xx/5xx errors.
  - **Alarms**: Low CPU utilisation, ECS task failure rates.

---

## **Tests**
### **Unit Tests**
- **Python**: Run `pytest` for backend and preprocessing modules.
- **JavaScript**: Run `npm test` for frontend testing.

### **Integration Tests**
- Mock AWS S3 interactions and test data loading.

---

## **Security**
- **Snyk Scans**: Ensures secure dependencies in Python, JavaScript, and Terraform configurations.
- **IAM Policies**: Restrict ECS task roles to only necessary permissions.
- **Secrets Management**: Uses AWS Secrets Manager for API keys.

---

## **Future Enhancements**

- Integrate more custom metrics for advanced monitoring.
- Implement load testing to simulate high-traffic scenarios.

---
