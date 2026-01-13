"""Built-in permission presets."""

PRESETS: dict[str, dict] = {
    "developer": {
        "permissions": {
            "allow": [
                "Bash(git *)",
                "Bash(npm *)",
                "Bash(npx *)",
                "Bash(yarn *)",
                "Bash(pnpm *)",
                "Bash(uv *)",
                "Bash(pip *)",
                "Bash(python *)",
                "Bash(node *)",
                "Bash(make *)",
                "Bash(cargo *)",
                "Bash(go *)",
            ]
        }
    },
    "git": {
        "permissions": {
            "allow": [
                "Bash(git *)",
                "Bash(gh *)",
            ]
        }
    },
    "node": {
        "permissions": {
            "allow": [
                "Bash(npm *)",
                "Bash(npx *)",
                "Bash(yarn *)",
                "Bash(pnpm *)",
                "Bash(node *)",
            ]
        }
    },
    "python": {
        "permissions": {
            "allow": [
                "Bash(uv *)",
                "Bash(pip *)",
                "Bash(python *)",
                "Bash(pytest *)",
                "Bash(ruff *)",
            ]
        }
    },
    "docker": {
        "permissions": {
            "allow": [
                "Bash(docker *)",
                "Bash(docker-compose *)",
            ]
        }
    },
    "k8s": {
        "permissions": {
            "allow": [
                "Bash(kubectl *)",
                "Bash(helm *)",
            ]
        }
    },
}
