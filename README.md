# nu-blender

A work-in-progress, modern Blender add-on that adds import support for scene files (`.nup`) from the PC version of *LEGO Star Wars: The Video Game*.

## Building

Before building the add-on, make sure to add the Blender installation directory to your `PATH`.

### On Windows

You MUST use a PowerShell prompt.

#### Step 1: Clone the repo

```powershell
git clone https://github.com/IsaMorphic/nu-blender.git
cd nu-blender
```

#### Step 2: Allow script execution

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
```

#### Step 3: Build the extension

```powershell
.\scripts\build.ps1
```

#### On Linux

Use your favorite Terminal app!

#### Step 1: Clone the repo

```shell
git clone https://github.com/IsaMorphic/nu-blender.git
cd nu-blender
```

#### Step 2: Build the extension

```shell
sh .\scripts\build.sh
```

#### On macOS

Use the built-in Terminal app.

#### Step 1: Clone the repo

```shell
git clone https://github.com/IsaMorphic/nu-blender.git
cd nu-blender
```

#### Step 2: Build the extension

```shell
zsh .\scripts\build.sh
```