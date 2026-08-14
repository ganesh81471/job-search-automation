import urllib.parse


class JobUrlBuilder:
    def __init__(self, keywords, location="India", hours=24):
        self.keywords = keywords
        self.location = location
        self.hours = hours  # 24, 48, or 168 (1 week) -> LinkedIn's f_TPR=r<seconds>

    def build_linkedin_url(self, experience_levels=None):
        """Generates public LinkedIn search URL filtered for freshness.
        experience_levels: optional list of LinkedIn's f_E codes to pre-filter
                            server-side: 1=Internship, 2=Entry level. Using this
                            cuts down how many irrelevant senior jobs we even
                            have to fetch/classify."""
        encoded_keywords = urllib.parse.quote(self.keywords)
        encoded_location = urllib.parse.quote(self.location)
        seconds = int(self.hours) * 3600
        url = (f"https://www.linkedin.com/jobs/search/?keywords={encoded_keywords}"
               f"&location={encoded_location}&f_TPR=r{seconds}")
        if experience_levels:
            url += f"&f_E={','.join(str(e) for e in experience_levels)}"
        return url

    def build_linkedin_posts_url(self):
        query = f"{self.keywords} hiring {self.location}"
        encoded_query = urllib.parse.quote(query)
        return f"https://www.linkedin.com/search/results/content/?keywords={encoded_query}&sortBy=%22date_posted%22"


if __name__ == "__main__":
    builder = JobUrlBuilder(keywords="Embedded Firmware", location="India", hours=168)
    print("LinkedIn Jobs URL (1 week, entry+internship only):\n",
          builder.build_linkedin_url(experience_levels=[1, 2]))