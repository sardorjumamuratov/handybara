import json


class Item:
    def __init__(self, name, added_at, added_by):
        self.name = name
        self.added_at = added_at
        self.added_by = added_by


class DeletedItem(Item):
    def __init__(self, deleted_by, deleted_date, was_done, name, added_at, added_by):
        super().__init__(name, added_at, added_by)
        self.deleted_by = deleted_by
        self.deleted_date = deleted_date
        self.was_done = was_done


class DeletedItemEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, DeletedItem):
            return {"deleted_by": obj.deleted_by,
                    "deleted_date": obj.deleted_date,
                    "was_done": obj.was_done,
                    "name": obj.name,
                    "added_at": obj.added_at,
                    "added_by": obj.added_by
                    }
        return super().default(obj)
