import factory
from apps.agent.models import Repository, ResearchSession, Finding


class RepositoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Repository

    # Generates unique matching URLs and names sequentially
    url = factory.Sequence(lambda n: f"https://github.com/mockuser/repo-variant-{n}")
    name = factory.Sequence(lambda n: f"repo-variant-{n}")


class ResearchSessionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ResearchSession

    repository = factory.SubFactory(RepositoryFactory)
    question = "What is the primary architectural pattern used here?"
    final_answer = "The codebase follows a standard clean service-layer design."
    token_usage = 150


class FindingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Finding

    session = factory.SubFactory(ResearchSessionFactory)
    tool_name = "list_github_files"
    input_data = factory.LazyFunction(lambda: {"path": ""})
    output_data = "manage.py\napps/\nrequirements.txt"
    conclusion = "Inspected root directories to evaluate file structures."
