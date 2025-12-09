# Cyoda Data Agent - Credential Reuse Guide

## Overview

The Cyoda Data Agent now **automatically reuses credentials** from your session. Once you provide your credentials in the first request, you don't need to provide them again for subsequent requests in the same conversation.

---

## How It Works

### First Request (Provide Credentials)
```
User: "Search my Cyoda environment for all cats.
       My client_id is F7NN4O, 
       secret is KyTcXdJL4QVDS9T1dQoQ, 
       host is https://client-05e11da2107844fc944ee5b872fcb6b6-dev.kube3.cyoda.org"

Agent: [Stores credentials in session]
       "I'll search for cats in your environment..."
       [Executes search with your credentials]
```

### Subsequent Requests (Credentials Reused)
```
User: "Now find all black cats"

Agent: [REUSES stored credentials - no need to ask]
       "I'll search for black cats in your environment..."
       [Executes search with SAME credentials]

User: "Get the cat with ID abc123"

Agent: [REUSES stored credentials]
       "I'll retrieve that cat from your environment..."
       [Executes get with SAME credentials]

User: "Create a new cat named Whiskers"

Agent: [REUSES stored credentials]
       "I'll create a new cat in your environment..."
       [Executes create with SAME credentials]
```

---

## Switching Environments

If you want to switch to a different environment, just provide new credentials:

```
User: "Switch to my production environment.
       Use client_id prod123, 
       secret prod456, 
       host https://prod-env.cyoda.org"

Agent: [UPDATES stored credentials to new ones]
       "I'll switch to your production environment..."
       [All subsequent requests use NEW credentials]

User: "Search for all cats"

Agent: [REUSES NEW credentials from production]
       "I'll search for cats in your production environment..."
```

---

## Key Rules

✅ **Reuse credentials** - Once provided, used for all subsequent requests  
✅ **Only ask once** - First request only, or when you provide new credentials  
✅ **Automatic switching** - Provide new credentials to switch environments  
✅ **Session-based** - Credentials are stored for the current conversation  
✅ **Mention environment** - Agent tells you which environment is being used  

❌ **Don't repeat credentials** - No need to provide them again  
❌ **Don't switch silently** - Agent won't change environments without your request  

---

## Example Workflow

```
1. User provides credentials + first request
   → Agent stores credentials, executes request

2. User makes second request (no credentials)
   → Agent reuses stored credentials, executes request

3. User makes third request (no credentials)
   → Agent reuses stored credentials, executes request

4. User provides NEW credentials + request
   → Agent updates stored credentials, executes request

5. User makes fifth request (no credentials)
   → Agent reuses NEW credentials, executes request
```

---

## Benefits

🚀 **Faster interactions** - No need to repeat credentials  
🎯 **Cleaner conversations** - Focus on what you want to do  
🔒 **Secure** - Credentials stored only in session memory  
✨ **Seamless** - Works automatically, no configuration needed  

---

## When Credentials Are Needed

You MUST provide credentials when:
- Making your **first request** to the agent
- **Switching to a different environment**
- Your **session expires** (new conversation)

You DON'T need to provide credentials when:
- Making **subsequent requests** in the same conversation
- Using the **same environment** as before

