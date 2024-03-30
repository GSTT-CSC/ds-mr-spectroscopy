from aide_sdk.application import AideApplication
from mrs.MRSOperator import MRSOperator

if __name__ == "__main__":
    AideApplication.start(operator=MRSOperator())
