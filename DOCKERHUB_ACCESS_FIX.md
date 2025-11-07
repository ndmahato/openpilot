# Docker Hub Repository Access Fix

## Problem

The error `pull access denied for kainosit/openpilot` means the Docker Hub repository is **private** and requires authentication, or doesn't exist.

## Solution Options

Choose ONE of the following solutions:

---

## Option 1: Make Repository Public (Recommended - Easiest)

### Steps:

1. **Visit Docker Hub:**
   - Go to: https://hub.docker.com/
   - Login with your credentials

2. **Navigate to Repository:**
   - Click on "Repositories"
   - Find `kainosit/openpilot`
   - Click on it

3. **Make Public:**
   - Click on "Settings" tab
   - Scroll to "Visibility"
   - Change from "Private" to "Public"
   - Click "Save"

4. **Test on EC2:**
   ```bash
   # No login needed now
   docker pull kainosit/openpilot:latest
   ./deploy-ec2.sh
   ```

### Pros:
- ✅ No authentication needed on EC2
- ✅ Easier deployment
- ✅ Can share with others

### Cons:
- ⚠️ Anyone can pull your image (but not push)
- ⚠️ Image layers visible on Docker Hub

---

## Option 2: Login to Docker Hub on EC2

### Steps:

1. **On EC2, login to Docker Hub:**
   ```bash
   docker login
   # Enter username: kainosit
   # Enter password: YOUR_PASSWORD_OR_TOKEN
   ```

2. **Run deployment:**
   ```bash
   ./deploy-ec2.sh
   # Will now successfully pull the private image
   ```

### Use Personal Access Token (More Secure):

1. **Create Token:**
   - Visit: https://hub.docker.com/settings/security
   - Click "New Access Token"
   - Name: "EC2-Production"
   - Access: Read-only
   - Click "Generate"
   - Copy the token (you'll only see it once!)

2. **Login on EC2 with token:**
   ```bash
   docker login -u kainosit
   # Paste the token as password (not your account password)
   ```

### Pros:
- ✅ Repository stays private
- ✅ More secure with access tokens
- ✅ Can revoke token anytime

### Cons:
- ⚠️ Need to login on every EC2 instance
- ⚠️ Token needs to be managed securely

---

## Option 3: Build from Source on EC2

If you can't or don't want to use Docker Hub, build directly on EC2.

### Steps:

1. **Upload source files to EC2:**
   ```powershell
   # From Windows
   scp -i "C:\path\to\key.pem" `
     Dockerfile `
     test_yolo_multi_mobile.py `
     requirements.txt `
     SYSTEM_DOCUMENTATION.md `
     docker-compose.yml `
     docker-compose.override.yml `
     ubuntu@YOUR_EC2_IP:~/OpenPilot/
   ```

2. **On EC2, build and run:**
   ```bash
   cd ~/OpenPilot
   
   # Build locally (takes 5-10 minutes first time)
   docker compose up --build -d
   ```

3. **Or use the updated deploy-ec2.sh:**
   ```bash
   # The script will automatically detect source files
   # and build if pull fails
   ./deploy-ec2.sh
   ```

### Pros:
- ✅ No Docker Hub needed
- ✅ Full control over build
- ✅ No authentication issues

### Cons:
- ⚠️ Slower first deployment (5-10 min build)
- ⚠️ Uses EC2 bandwidth for downloading dependencies
- ⚠️ Need source files on EC2

---

## Quick Fix Instructions

### If you're stuck on EC2 right now:

**Immediate workaround (build from source):**

```bash
cd ~/OpenPilot

# If you have source files already:
docker compose up --build -d

# If not, upload them first from Windows:
# scp -i key.pem Dockerfile test_yolo_multi_mobile.py requirements.txt ubuntu@EC2_IP:~/OpenPilot/
```

**Permanent fix (make repo public):**

1. Visit: https://hub.docker.com/repository/docker/kainosit/openpilot/settings/general
2. Change Visibility to "Public"
3. Save
4. Back on EC2: `docker pull kainosit/openpilot:latest` (should work now)

---

## Verify Access

Test if your repository is public:

```bash
# On any machine (without docker login):
docker pull kainosit/openpilot:latest

# If this works without login = public ✓
# If it asks for login = private ⚠️
```

Or use the verification script:

```bash
chmod +x check-dockerhub.sh
./check-dockerhub.sh
```

---

## Updated Deploy Script

The `deploy-ec2.sh` script has been updated to:

1. **Try to pull from Docker Hub first**
2. **If pull fails**, check for source files
3. **If source files exist**, build locally automatically
4. **If nothing works**, show helpful error message

So you can just run:

```bash
./deploy-ec2.sh
```

And it will handle the fallback automatically!

---

## Recommendation

**For this project, I recommend Option 1 (Make Public)** because:

- ✅ Fastest deployment
- ✅ No authentication management
- ✅ Easier to document and share
- ✅ Image is already large (12GB), making it public doesn't add risk
- ✅ Code functionality is visible in your GitHub repo anyway

The main code is in `test_yolo_multi_mobile.py` which is likely in your GitHub repo, so the Docker image being public doesn't expose anything new.

---

## Security Note

If your image contains:
- API keys
- Passwords
- Sensitive configuration
- Proprietary code

Then keep it **private** and use **Option 2** (Docker login with tokens).

But since this is an object detection system with standard open-source components (YOLOv8, Tesseract, Flask), making it public is fine.

---

## Next Steps

1. **Choose your option** (1, 2, or 3 above)
2. **Follow the steps**
3. **Run `./deploy-ec2.sh` again**
4. **Check with:** `docker ps` to see container running

Need help? Check:
- QUICK_DEPLOY.md
- EC2_DEPLOYMENT_GUIDE.md
- DEPLOYMENT_TESTING_CHECKLIST.md
