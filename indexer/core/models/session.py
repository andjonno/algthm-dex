"""
IndexSession model.
"""


from lib.models.base_model import BaseModel


class Session(BaseModel):

    def progress(self):
        total = self.get('total')
        errors = self.get('errors')
        feed = self.get('feed')
        return (total - errors) / (feed * 1.0)

    def repos_remaining(self):
        total = self.get('total')
        errors = self.get('errors')
        feed = self.get('feed')
        return total - feed - errors
