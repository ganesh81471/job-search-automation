import urllib.parse

class JobUrlBuilder:
    def __init__(self, keywords, location="India"):
        self.keywords = keywords
        self.location = location

    def build_linkedin_url(self):
        """Generates public LinkedIn search URL filtered for the last 24 hours (86400 seconds)."""
        encoded_keywords = urllib.parse.quote(self.keywords)
        encoded_location = urllib.parse.quote(self.location)
        
        # f_TPR=r86400 filters jobs posted in past 24 hrs
        return f"https://www.linkedin.com/jobs/search/?keywords={encoded_keywords}&location={encoded_location}&f_TPR=r86400"

    def build_naukri_url(self):
        """Generates public Naukri search URL filtered for 1-day freshness."""
        # Convert 'Embedded Firmware' -> 'embedded-firmware' for Naukri URL structure
        formatted_keywords = self.keywords.lower().replace(" ", "-")
        formatted_location = self.location.lower().replace(" ", "-")
        
        # freshness=1 filters for jobs posted today/past 24h
        return f"https://www.naukri.com/{formatted_keywords}-jobs-in-{formatted_location}?freshness=1"


if __name__ == "__main__":
    # Quick test of our URL builder
    builder = JobUrlBuilder(keywords="Embedded Firmware", location="India")
    print("LinkedIn Target URL:\n", builder.build_linkedin_url())
    print("\nNaukri Target URL:\n", builder.build_naukri_url())