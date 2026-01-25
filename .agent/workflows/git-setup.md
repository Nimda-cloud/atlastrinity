---
description: Configure Git user identity for commits
---

To ensure you can commit changes in this repository, run the appropriate setup command.

### 1. Developer Identity (Kizyma Oleg)
// turbo
```zsh
git config user.name "Kizyma Oleg"
git config user.email "oleg1203@gmail.com"
```

### 2. Antigravity Agent Identity
// turbo
```zsh
git config user.name "Antigravity AI"
git config user.email "antigravity-bot@google.com"
```

### 3. Windsurf Agent Identity
// turbo
```zsh
git config user.name "Windsurf AI"
git config user.email "windsurf-bot@codeium.com"
```

### 4. (Optional) Verify configuration
```zsh
git config --list | grep user
```

### 5. Force use of Token from `.env`
If Git still asks for login, run:
```zsh
git remote set-url origin https://<TOKEN>@github.com/Nimda-cloud/atlastrinity
```
*(Замініть `<TOKEN>` на значенння з вашого `.env`)*
