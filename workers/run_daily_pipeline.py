"""CLI entry point for the daily signal detection pipeline."""
import asyncio

from api.schemas import InteractionExtractionRequest, PageSourceInput
from workers.jobs import extract_public_activity_signals


async def main() -> None:
    """Run a placeholder daily pipeline until scheduled sources are configured."""
    request = InteractionExtractionRequest(
        sources=[
            PageSourceInput(
                source_type="text",
                label="daily-pipeline-placeholder",
                text="No scheduled sources configured yet.",
            )
        ]
    )
    await extract_public_activity_signals(request)


if __name__ == "__main__":
    asyncio.run(main())
