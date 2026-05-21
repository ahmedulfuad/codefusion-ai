class BaseService:
    model = None

    def __init__(self):
        if not self.model:
            raise NotImplementedError("Service classes must define a 'model' attribute.")

    def create(self, **kwargs):
        """Generic method to create a model instance."""
        return self.model.objects.create(**kwargs)
