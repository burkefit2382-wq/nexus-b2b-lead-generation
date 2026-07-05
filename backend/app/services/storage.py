from . import config


def r2_configured() -> bool:
    return all(
        [
            config.R2_ACCESS_KEY,
            config.R2_SECRET_KEY,
            config.R2_BUCKET,
            config.R2_ENDPOINT_URL,
        ]
    )
