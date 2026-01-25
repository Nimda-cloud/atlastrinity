---
description: Configure Git user identity for commits
---

To ensure you can commit changes in this repository, run the following commands:

// turbo-all
1. Set user name:
```zsh
git config user.name "Kizyma Oleg"
```

2. Set user email:
```zsh
git config user.email "oleg1203@gmail.com"
```

3. (Optional) Verify configuration:
```zsh
git config --list | grep user
```

4. Force use of Token from `.env`:
If Git still asks for login, run:
```zsh
git remote set-url origin https://<TOKEN>@github.com/Nimda-cloud/atlastrinity
```
*(Замініть `<TOKEN>` на значенння з вашого `.env`)*
