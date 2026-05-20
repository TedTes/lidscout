"""Runtime dependency wiring for API routes."""
from adapters.hackernews import HackerNewsActivityAdapter
from adapters.reddit import RedditActivityAdapter
from api.routes.signals import SignalApiDependencies


def build_signal_api_dependencies() -> SignalApiDependencies:
    """Build signal API dependencies from runtime configuration."""
    return SignalApiDependencies(
        reddit_adapter=RedditActivityAdapter(),
        hackernews_adapter=HackerNewsActivityAdapter(),
    )
