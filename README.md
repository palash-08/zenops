# ZenOps

ZenOps is an AI-powered infrastructure assistant that helps developers manage their Linux servers using natural language.

Instead of manually SSH-ing into multiple VPSs and remembering what changed on each server, you can simply ask ZenOps to investigate problems, perform routine maintenance, and keep track of previous incidents.

Unlike traditional AI assistants, ZenOps remembers the history of your infrastructure. It can recall previous issues, successful fixes, and important context before making decisions, allowing it to become more helpful over time. It grows WITH you.

## What can it do?

- Manage multiple Linux servers from one place
- Investigate server issues using AI
- Execute approved maintenance tasks
- Remember previous incidents and their resolutions
- Learn from past interactions using persistent memory
- Reduce repetitive DevOps work

## Example

Instead of logging into your server and running multiple commands yourself:

```text
SSH into server
↓

Check logs
↓

Inspect Docker
↓

Restart services
↓

Remember what happened
```

You can simply ask:

```text
"Investigate why my production server keeps restarting."

or

"Restart Nginx on the production server."
```

ZenOps will:

- Analyze the request
- Recall relevant past incidents
- Investigate the server
- Suggest or perform an appropriate action (with approval where required)
- Remember the outcome for future use

## Project Status

🚧 Currently under active development.

Core backend, AI integration, and infrastructure management features are being built incrementally.

## License

MIT