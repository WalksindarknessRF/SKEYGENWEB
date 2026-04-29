# SKEYGEN Web Interface for Raspberry Pi

A web-based interface for the Motorola System Key Generation Utility (SKEYGEN.EXE). Once installed on a Raspberry Pi, anyone on your local network can open a browser, enter a Motorola System ID, and download the generated `.KEY` file — no DOS, no emulator knowledge required.

---

## What You Need Before Starting

- A **Raspberry Pi** (Zero W, Zero 2 W, Pi 3, or Pi 4)
- A **MicroSD card** (8GB or larger)
- A **MicroSD card reader** for your computer
- Your copy of **SKEYGEN.EXE**
- A **Windows, Mac, or Linux computer** to set things up
- Your Pi connected to your **local network via WiFi or ethernet**
- An **internet connection** on the Pi during install

---

## Part 1 — Prepare the Raspberry Pi

### Step 1: Download Raspberry Pi Imager

Go to **https://www.raspberrypi.com/software/** and download the Raspberry Pi Imager for your computer. Install and open it.

### Step 2: Flash the SD Card

1. Insert your MicroSD card into your computer
2. Open Raspberry Pi Imager
3. Click **"Choose Device"** and select your Pi model
4. Click **"Choose OS"** → **Raspberry Pi OS (other)** → **Raspberry Pi OS Lite (64-bit)**
5. Click **"Choose Storage"** and select your MicroSD card
6. Click **"Next"**
7. When asked about customisation settings click **"Edit Settings"**

### Step 3: Configure WiFi and SSH in the Imager

In the settings screen:

- Check **"Set hostname"** → type `raspberrypi`
- Check **"Set username and password"** → set a username and password you'll remember
- Check **"Configure wireless LAN"** → enter your WiFi name and password and set your country code
- Click the **"Services"** tab → check **"Enable SSH"** → select **"Use password authentication"**
- Click **"Save"** → **"Yes"** → confirm erasing the card

Wait 2-5 minutes for it to finish writing.

### Step 4: Boot the Pi

Remove the MicroSD card from your computer, insert it into the Pi, and connect power. Wait **60-90 seconds** for the first boot to complete.

### Step 5: Find the Pi's IP Address

You need the Pi's IP address to connect to it. Try one of these:

- **Check your router** — log into your router admin page (usually http://192.168.1.1) and look for a device called `raspberrypi` in the connected devices list
- **Windows Command Prompt** — type `ping raspberrypi.local` and the IP will appear in the response

Write down the IP address — it will look like `192.168.1.45`.

---

## Part 2 — Connect to the Pi

You'll control the Pi remotely using SSH.

### On Windows 10/11

Open **Command Prompt** or **PowerShell** and type:
```
ssh pi@192.168.1.45
```
Replace `192.168.1.45` with your Pi's actual IP and `pi` with your username.

When asked "Are you sure you want to continue connecting?" type `yes` and press Enter. Enter your password when prompted — you won't see anything as you type, that's normal.

You should now see:
```
pi@raspberrypi:~ $
```
You're connected. Everything you type now runs on the Pi.

### On Mac or Linux

Open **Terminal** and type:
```
ssh pi@192.168.1.45
```

---

## Part 3 — Copy Files to the Pi

Leave your SSH window open. Open a **second** Command Prompt or Terminal window on your computer and run:

### Windows
```
scp -r skeygen-web pi@192.168.1.45:~
scp SKEYGEN.EXE pi@192.168.1.45:~/skeygen-web/
```

### Mac / Linux
```
scp -r skeygen-web pi@192.168.1.45:~
scp SKEYGEN.EXE pi@192.168.1.45:~/skeygen-web/
```

Enter your Pi password when prompted. `SKEYGEN.EXE` is not included in this repo and must be obtained through legitimate Motorola/Motorola Solutions channels.

---

## Part 4 — Run the Installer

Go back to your SSH window and run:

```bash
cd ~/skeygen-web
sudo bash install.sh
```

The installer will automatically:
- Install DOSBox-X (the x86 emulator that runs the DOS program)
- Install Python and the web server
- Download a FreeDOS image (~32MB)
- Configure SKEYGEN.EXE on the virtual DOS drive
- Set everything up to start automatically on boot

This takes **5-15 minutes** depending on your internet speed. When complete you'll see:

```
========================================================
  SKEYGEN web interface installed successfully!
========================================================

  Open your browser to:  http://192.168.1.45:5000
```

---

## Part 5 — Use the Web Interface

Open a browser on any device on the same network and go to:

```
http://192.168.1.45:5000
```

Enter a Motorola System ID (1-6 hexadecimal characters, e.g. `1FC` or `1A2B3C`) and click **Generate System Key File**.

> ⚠️ **Key generation takes time.** On a Pi Zero W expect approximately 45 seconds. On a Pi Zero 2 W, Pi 3, or Pi 4 expect 10-15 seconds. The page shows a spinner while working — do not close the tab or click again. Just wait.

When finished the `.KEY` file downloads automatically.

---

## The Pi Starts Automatically

The service starts automatically every time the Pi boots. Just power it on, wait 30 seconds, and the web interface is ready. No login required.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "This site can't be reached" | Wait 60 seconds after boot, check IP address, try `sudo systemctl restart skeygen` |
| Generation fails with error | Try again — timing occasionally varies on first attempt |
| Page spins more than 2 minutes | SSH in and run `sudo killall dosbox-x` then `sudo systemctl restart skeygen` |
| Can't connect via SSH | Wait 90 seconds after power on, verify you're on the same WiFi network |
| Forgot the Pi's IP | SSH in and run `hostname -I` |

---

## Service Management

```bash
sudo systemctl status skeygen      # Is it running?
sudo systemctl restart skeygen     # Restart it
sudo journalctl -u skeygen -f      # Watch live logs
sudo killall dosbox-x              # Kill stuck emulator processes
```

---

## Performance by Hardware

| Pi Model | Generation Time |
|----------|----------------|
| Pi Zero W | ~45 seconds |
| Pi Zero 2 W | ~15 seconds |
| Pi 3 B / B+ | ~10 seconds |
| Pi 4 | ~8 seconds |

---

## Security Note

This interface has no password protection and is intended for **trusted local networks only**. Do not expose port 5000 to the internet.

---

## About

This project wraps the original Motorola SKEYGEN.EXE (© Motorola Inc. 1989) in a modern web interface using Flask, DOSBox-X, FreeDOS, and a TCP serial bridge to drive the interactive DOS program automatically. SKEYGEN.EXE is not included and must be supplied by the user.
