# AI Integration

## Extension Point

The bookworm-hole-api provides an extension point for AI features via the `AIProvider` interface.

### Base Interface

All AI providers must implement `app.services.ai.base.AIProvider`:

```python
class AIProvider(ABC):
    @abstractmethod
    def generate_summary(self, text: str) -> str:
        """Generate a summary of the given text."""
        pass

    @abstractmethod
    def suggest_tags(self, book: Book) -> list[str]:
        """Suggest tags for a book based on its metadata."""
        pass

    @abstractmethod
    def recommend(self, user_id: UUID, n: int) -> list[UUID]:
        """Recommend book IDs for a user."""
        pass
```

### Default Implementation

By default, the API uses `NoOpAIProvider`, which returns empty/default values for all methods:

- `generate_summary()` → empty string
- `suggest_tags()` → empty list
- `recommend()` → empty list

## Configuration

Set `AI_PROVIDER` environment variable to select which provider to use:

```bash
AI_PROVIDER=noop  # Default, no-op provider
```

## Implementing a Custom Provider

1. Create a new class inheriting from `AIProvider`
1. Implement all abstract methods
1. Register it in `app.core.deps.get_ai_provider()`:

```python
def get_ai_provider() -> AIProvider:
    settings = get_settings()
    provider_name = settings.ai_settings.provider

    if provider_name == "noop":
        return NoOpAIProvider()
    elif provider_name == "my_provider":
        return MyCustomProvider()

    raise ValueError(f"Unknown AI provider: {provider_name}")
```

4. Set `AI_PROVIDER=my_provider` in `.env`

## Using the Provider

Inject the provider as a dependency in routers/services:

```python
from fastapi import Depends
from app.core.deps import get_ai_provider
from app.services.ai.base import AIProvider

@router.post("/ai/summary")
async def summarize(text: str, ai: AIProvider = Depends(get_ai_provider)):
    return await ai.generate_summary(text)
```
