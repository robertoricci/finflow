# Patch: app/controllers/auth_controller.py

## 1. Adicionar import no topo:
```python
from datetime import datetime, timedelta
```

## 2. Substituir criação do User no register():

**ANTES:**
```python
user = User(name=name, email=email)
user.set_password(password)
```

**DEPOIS:**
```python
trial_expires = datetime.utcnow() + timedelta(days=15)
user = User(
    name=name, email=email,
    plan_status='trial',
    plan_expires_at=trial_expires,
)
user.set_password(password)
```
