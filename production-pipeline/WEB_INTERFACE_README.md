# 🌐 Web Interface for GCS Video Automations

**Access your trivia video generator from any computer!** This web interface provides a beautiful, mobile-friendly way to generate trivia videos without touching the terminal.

## 🚀 Quick Start

### 1. **Set Environment Variables**
```bash
# Set your Gemini API key
export GEMINI_API_KEY="your-actual-gemini-api-key-here"

# Set your Google Cloud credentials path
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account-key.json"
```

### 2. **Deploy the Web Interface**
```bash
# Make the deployment script executable
chmod +x deploy_web_interface.sh

# Run the deployment script
./deploy_web_interface.sh
```

### 3. **Access from Any Computer**
- **Local**: http://localhost:5000
- **Network**: http://YOUR_IP_ADDRESS:5000
- **Mobile**: Works on phones and tablets!

## 🎯 Features

### **✨ Beautiful Interface**
- Modern, responsive design
- Mobile-friendly layout
- Real-time progress updates
- Live job status tracking

### **🚀 One-Click Generation**
- Select number of questions (3, 5, 7, or 10)
- Choose category (Sports, Science, History, etc.)
- Click "Generate" and watch the magic happen!

### **📊 Real-Time Monitoring**
- Live progress bars
- Step-by-step status updates
- Job completion notifications
- Statistics dashboard

### **🌐 Access from Anywhere**
- Works on any device with a web browser
- Accessible from any computer on your network
- No software installation required

## 🔧 Manual Setup (Alternative)

If you prefer to set up manually:

### 1. **Install Dependencies**
```bash
# Create virtual environment
python3 -m venv venv_web
source venv_web/bin/activate

# Install requirements
pip install -r requirements_web.txt
```

### 2. **Run the Web Interface**
```bash
python web_interface.py
```

### 3. **Access the Interface**
Open your browser and go to: http://localhost:5000

## 🌍 Making It Internet Accessible

### **Option 1: Router Port Forwarding**
1. Configure your router to forward port 5000 to your computer
2. Use your public IP address to access from anywhere
3. **Note**: This exposes your computer to the internet

### **Option 2: ngrok (Recommended for Testing)**
```bash
# Install ngrok
brew install ngrok  # macOS
# or download from https://ngrok.com/

# Create tunnel
ngrok http 5000

# Share the ngrok URL with anyone
```

### **Option 3: Google Cloud Run (Production)**
1. Containerize the application
2. Deploy to Google Cloud Run
3. Get a public HTTPS URL
4. Scale automatically

## 📱 Using the Interface

### **Step 1: Configure Generation**
- **Number of Questions**: Choose 3, 5, 7, or 10
- **Category**: Select from Sports, Science, History, or General Knowledge
- **Click**: "🚀 Generate Trivia Video"

### **Step 2: Monitor Progress**
- **Progress Bar**: Shows completion percentage
- **Status Updates**: Real-time step-by-step progress
- **Live Updates**: No need to refresh the page

### **Step 3: Get Your Video**
- **Completion Notification**: When generation finishes
- **Video Link**: Click to view in Google Cloud Console
- **Download**: Use gsutil to download the video

## 🔍 Troubleshooting

### **Common Issues**

#### **"GEMINI_API_KEY not configured"**
```bash
export GEMINI_API_KEY="your-actual-key-here"
```

#### **"GOOGLE_APPLICATION_CREDENTIALS not configured"**
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials.json"
```

#### **"Module not found" errors**
```bash
# Make sure you're in the right directory
cd production-pipeline

# Reinstall requirements
source venv_web/bin/activate
pip install -r requirements_web.txt
```

#### **Port 5000 already in use**
```bash
# Find what's using port 5000
lsof -i :5000

# Kill the process or change the port in web_interface.py
```

### **Network Access Issues**

#### **Can't access from other computers**
1. Check firewall settings
2. Ensure you're using `0.0.0.0` as host (already configured)
3. Verify network permissions

#### **Mobile devices can't connect**
1. Ensure both devices are on the same network
2. Use the computer's local IP address (not localhost)
3. Check mobile browser compatibility

## 🎨 Customization

### **Changing the Port**
Edit `web_interface.py`:
```python
socketio.run(app, host='0.0.0.0', port=8080, debug=True)  # Change 5000 to 8080
```

### **Adding New Categories**
Edit `web_interface.py` and `templates/index.html`:
1. Add new prompt preset in `GeminiFeederFixed`
2. Add new option in the HTML select dropdown
3. Update the generation logic

### **Modifying the UI**
Edit `templates/index.html`:
- Colors and styling in the `<style>` section
- Layout and components in the HTML
- JavaScript functionality in the `<script>` section

## 📊 API Endpoints

The web interface provides several API endpoints:

- **`/`**: Main interface
- **`/generate`**: Start video generation (POST)
- **`/jobs`**: List all jobs
- **`/jobs/<job_id>`**: Get specific job status
- **`/health`**: Health check

## 🔒 Security Considerations

### **Production Deployment**
- Change the default secret key
- Use HTTPS in production
- Implement user authentication
- Rate limit API endpoints
- Monitor for abuse

### **Network Security**
- Only expose necessary ports
- Use firewall rules
- Consider VPN access
- Regular security updates

## 🚀 Performance Tips

### **Optimization**
- Use production WSGI server (gunicorn)
- Enable caching for static assets
- Monitor memory usage
- Scale horizontally if needed

### **Monitoring**
- Check `/health` endpoint
- Monitor job completion times
- Track error rates
- Monitor resource usage

## 📚 Related Documentation

- **Core Pipeline**: See `README.md` for main pipeline documentation
- **Testing Framework**: See `TESTING_README.md` for testing
- **Cloud Infrastructure**: See `cloud-infrastructure/` for deployment

## 🎉 Success Stories

### **Use Cases**
- **Content Creators**: Generate videos for social media
- **Educators**: Create educational content
- **Businesses**: Marketing and training videos
- **Personal Projects**: Fun trivia content

### **Benefits**
- **No Technical Knowledge Required**: Just click and generate
- **Access from Anywhere**: Use any device with a browser
- **Professional Results**: Broadcast-quality video output
- **Scalable**: Handle multiple requests simultaneously

---

**🎬 Ready to generate amazing trivia videos? Deploy the web interface and start creating content from any computer!** 🚀✨
