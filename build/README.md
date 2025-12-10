# Building

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