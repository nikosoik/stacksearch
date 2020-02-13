FROM python:3.6-buster
MAINTAINER Nikos Oikonomou <nikos.oik93@gmail.com>

# Install build utilities
RUN apt-get update && apt-get install -y apt-utils tree gcc make apt-transport-https ca-certificates build-essential

# Check python env
RUN python3 --version
RUN pip3 --version

# Working dir for container
WORKDIR /usr/src/stacksearch

# Installing python dependencies spacy language model
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python3 -m spacy download en_core_web_sm

# Copy source files to the working directory
COPY src/ /src/
RUN tree /src/

ENTRYPOINT ["python3", "/src/demo.py"]
#CMD ["hybrid", "wordvec_models/fasttext_archive/ft_v0.6.1.bin", "wordvec_models/tfidf_archive/tfidf_v0.3.pkl", "wordvec_models/index/ft_v0.6.1_post_index.pkl", "wordvec_models/index/tfidf_v0.3_post_index.pkl", "wordvec_models/index/extended_metadata.pkl", "10"]
