# Quick Reference: Make This Repository Private

## ⚡ Fast Track (Web Interface)

1. Go to: https://github.com/ndmahato/openpilot/settings
2. Scroll to bottom → **Danger Zone**
3. Click **Change visibility** → **Make private**
4. Type `ndmahato/openpilot` to confirm
5. Click **I understand, change repository visibility**

Done! ✅

## ⚡ Fast Track (Command Line)

```bash
gh repo edit ndmahato/openpilot --visibility private
```

## 📋 Important Notes

- **This is a GitHub setting**, not a code change
- **Requires admin access** to the repository
- **Cannot be done through commits** or pull requests
- See `CONVERT_TO_PRIVATE_GUIDE.md` for detailed instructions

## ❓ Why Can't This Be Done via Code?

Repository visibility is a **GitHub platform setting** managed at the repository level through GitHub's API or web interface. It's similar to:
- Changing repository name
- Enabling/disabling features (Issues, Wiki, Discussions)
- Managing access permissions

These settings exist outside the repository's code and version control.

## 🔒 What Happens After Converting?

- Repository becomes invisible to public
- Only you and invited collaborators can access
- Existing forks may become independent
- GitHub Actions may need permission updates
- Some features may require GitHub Pro (for free accounts)

## 📚 More Information

For complete details, see [CONVERT_TO_PRIVATE_GUIDE.md](./CONVERT_TO_PRIVATE_GUIDE.md)
