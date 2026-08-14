import urllib.parse

class JobUrlBuilder:
    def __init__(self, keywords, location="India"):
        self.keywords = keywords
        self.location = location

    def build_linkedin_url(self):
        """Generates public LinkedIn search URL filtered for the last 24 hours."""
        encoded_keywords = urllib.parse.quote(self.keywords)
        encoded_location = urllib.parse.quote(self.location)
        return f"https://www.linkedin.com/jobs/search/?keywords={encoded_keywords}&location={encoded_location}&f_TPR=r86400"

    def build_linkedin_posts_url(self):
        """Generates LinkedIn public post search URL for hiring posts."""
        query = f"{self.keywords} hiring {self.location}"
        encoded_query = urllib.parse.quote(query)
        return f"https://www.linkedin.com/search/results/content/?keywords={encoded_query}&sortBy=%22date_posted%22"


if __name__ == "__main__":
    builder = JobUrlBuilder(keywords="Embedded Firmware", location="India")
    print("LinkedIn Jobs URL:\n", builder.build_linkedin_url())
    print("\nLinkedIn Posts URL:\n", builder.build_linkedin_posts_url())