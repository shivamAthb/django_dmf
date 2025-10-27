import traceback

from django.db import transaction, connection

from dm.utils.logging import logger


class BaseDataMigrationTask:
    def __init__(self, **kwargs):
        self.version = None
        self.run_in_public_schema = True
        self.run_in_custom_schema = True

    def _run(self):
        raise NotImplementedError

    @classmethod
    def get_current_schema_name(cls):
        return getattr(connection, "schema_name", None)

    def run(self, **kwargs):
        current_schema_name = self.get_current_schema_name()
        if current_schema_name is not None:
            if not self.run_in_public_schema and current_schema_name == "public":
                return (
                    True,
                    "Skipping running the data migration task in public schema.",
                )
            if not self.run_in_custom_schema and current_schema_name != "public":
                return (
                    True,
                    "Skipping running the data migration task in custom schema.",
                )

        if self.version is None:
            raise Exception(
                "Version not defined. Skipping running the data migration task."
            )

        prior_atomic = connection.in_atomic_block
        if not prior_atomic:
            transaction.set_autocommit(False)
        try:
            self._run()
        except Exception as e:
            logger.info(
                f"Exception occurred while running the Data Migration task - {str(e)}"
            )
            traceback.print_exc()
            if not prior_atomic:
                transaction.rollback()
                transaction.set_autocommit(True)
            return False, str(e)
        else:
            if not prior_atomic:
                transaction.commit()
                logger.info("Transaction committed!")
                transaction.set_autocommit(True)

        return True, None
