import pandas as pd
import logging
from .uhc_processor import UHCProcessor
from .njveterans_processor import NJVeteransProcessor
from .jewishhome_processor import JewishHomeProcessor

logger = logging.getLogger(__name__)


class BillingProcessor:
    """Factory class to create appropriate processor"""
    
    def __new__(cls, mode_key, mode_config, output_folder):
        """Return appropriate processor based on mode"""
        if mode_key == 'UHC':
            return UHCProcessor(mode_key, mode_config, output_folder)
        elif mode_key == 'NJVETERANS':
            return NJVeteransProcessor(mode_key, mode_config, output_folder)
        elif mode_key == 'JEWISHHOME':
            return JewishHomeProcessor(mode_key, mode_config, output_folder)
        else:
            raise ValueError(f"Unknown billing mode: {mode_key}")