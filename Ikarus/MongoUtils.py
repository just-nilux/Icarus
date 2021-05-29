import re
import pymongo
import logging

class MongoClient():
    def __init__(self, _host, _port) -> None:
        self.client = pymongo.MongoClient(host=_host, port=_port)
        self.logger = logging.getLogger('app.{}'.format(__name__))


    async def find(self, col, item) -> None:
        """
        This function reads the selected item from the given collection

        Args:
            col ([type]): [description]
            item ([type]): [description]
        """        
        pass


    async def insert(self, col, item) -> None:
        """
        This function writes the selected item into the collection 

        Args:
            col (str): Name of the collection: [live-trade | hist-trade | observer]
            item (dict): Dictionary item
        """        
        self.logger.info(f"Item written to [{col}]")
        return True

    async def update(self, col, item) -> None:
        """
        This function updates the selected item in the given collection

        Args:
            col (str): [description]
            item (dict): [description]
        """        
        pass

    async def insert_many(self, col, item_dict) -> None:
        """
        This function writes the selected item into the collection 

        Args:
            col (str): Name of the collection: [live-trade | hist-trade | observer]
            item (dict): Dictionary item
        """        
        for pair, pair_dict in item_dict.items():
            pair_dict['pair'] = pair
            await self.insert(col, pair_dict)

        return True

if __name__ == "__main__":
    pass