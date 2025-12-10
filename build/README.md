# Building

To build this plugin, a compatible installation of Blender should be listed in your `PATH` environment variable. Usually you can add this manually by accessing `~/.bashrc` on Linux or `~/.zshrc` on macOS. On Windows, search for "Edit Environment Variables for your Account" in the Start menu. 

## On Windows

You MUST use a PowerShell prompt.

### Step 1: Clone the repo

```powershell
git clone https://github.com/IsaMorphic/nu-blender.git
cd nu-blender
```

### Step 2: Allow script execution

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
```

### Step 3: Build the extension

```powershell
.\scripts\build.ps1
```

## On Linux

Use your favorite Terminal app!

### Step 1: Clone the repo

```shell
git clone https://github.com/IsaMorphic/nu-blender.git
cd nu-blender
```

### Step 2: Build the extension

```shell
sh .\scripts\build.sh
```

## On macOS

Use the built-in Terminal app.

### Step 1: Clone the repo

```shell
git clone https://github.com/IsaMorphic/nu-blender.git
cd nu-blender
```

### Step 2: Build the extension

```shell
zsh .\scripts\build.sh
```