# Usage

```shell
git clone https://github.com/stefanandonov/finki-fw-app
cd finki-fw-app
docker build -t streamlit-app .
docker run -p 8501:8501 streamlit-app
```

Open localhost:8501 after that to use the app.

Copy the Authentication and Cookie headers from fw.finki.ukim.mk (using inspect element on the browser).

Set the name, labs, profile and date and time. Press generate response. Verify that your firewall rules were created on fw.finki.ukim.mk