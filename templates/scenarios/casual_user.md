For the `instruction.md` you generate, use a **casual / conversational** style:

Write like a real person asking a colleague for help. The tone is informal and natural — first-person ("I just...", "Can you help me..."), sometimes vague, sometimes more specific. Vary the user's technical level: some users are confused and don't know the right terms, others know exactly what they want but express it casually.

Don't give all the information upfront; let some details be discoverable only by exploring the environment.

**Vary the style** — from vague and confused to clear but casual:

**Good examples**:

```
hey so theres a bunch of CSV files in /app/data/ and I need them combined into one big dataset. some of them have different column names for the same thing though? like "name" vs "full_name" and "amt" vs "amount". figure it out and write the merged result to /app/output/merged.csv
```

```
I inherited this project from someone who left. There's a script somewhere that generates reports but I can't figure out how to run it. The reports should end up as PDFs I think? Can you help me get it working and generate the report for the latest data?
```

```
I've put an image at /app/image.ppm that I rendered programmatically. Write a c program image.c that I can run and compile and will generate an image that's as close as possible to the image I put here. Specifically, I will compute the normalized L2 similarity in [0,1] and yours must match with 0.99 similarity. Your image.c file should not read image.ppm.
```

```
can you build me a simple web scraper? there's a list of URLs in /app/urls.txt and I need the main text content extracted from each page. save each one as a .txt file in /app/output/ named after the domain. oh and skip any that are PDFs
```

```
I have this old Python 2 script at /app/legacy/process.py that does some important data processing. nobody wants to maintain python 2 anymore. can you convert it to python 3 and make sure it still produces the same output? there's test data in /app/testdata/
```

```
the website is at /app/www/ — it's a static site but it loads super slow. can you optimize it? like compress the images, minify the CSS/JS, and maybe add some caching headers to the nginx config at /app/nginx/site.conf. i want it to score above 90 on lighthouse
```

**Remember**: Sound like a real person, not a specification. Some users are confused and vague, others are technically precise but still casual. The agent needs to investigate the environment to fill in any gaps. Keep requests natural — but there should be enough context that an agent exploring the filesystem can figure out the actual task.
