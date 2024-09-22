# Use an official Python runtime as a base image
#FROM python:3.12.2-slim
FROM python:3.12.2

# Set the working directory in the container
WORKDIR /app

# Install git to allow cloning Python packages from git repositories
RUN apt-get update && apt-get install -y git

#install cli [for debugging]
RUN apt-get install -y git bash

#upgrade pip
RUN pip install --upgrade pip

#install nano [for debugging]
RUN apt-get install -y nano

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
# no cache to make the docker image smaller
RUN pip install --no-cache-dir -r requirements.txt

# Download and install Geckodriver [for selenium]
RUN apt-get install -y wget \
    && wget https://github.com/mozilla/geckodriver/releases/download/v0.32.0/geckodriver-v0.32.0-linux64.tar.gz \
    && tar -xzf geckodriver-v0.32.0-linux64.tar.gz \
    && mv geckodriver /usr/local/bin/ \
    && rm geckodriver-v0.32.0-linux64.tar.gz

# Verify installation
RUN geckodriver --version

#install imagemagick [for moviepy && editing]
#only way I found that works is to clone the repo and build it from source
RUN apt-get install -y ghostscript
RUN git clone -b 7.1.1-38 --depth 1 https://github.com/ImageMagick/ImageMagick.git \
&& cd ImageMagick && \
./configure --without-magick-plus-plus --disable-docs --disable-static --with-tiff --with-jxl --with-tcmalloc && \
make && make install && \
ldconfig /usr/local/lib && \
rm -rf /ImageMagick


#update path for magick, make it executable
#for some ungodly reason, moviepy requires the env variables of FFMPEG_BINARY and IMAGEMAGICK_BINARY with the path to the binaries???
ENV IMAGEMAGICK_BINARY=/usr/local/bin/magick
ENV FFMPEG_BINARY=/usr/bin/ffmpeg

#install ffmpeg [for moviepy && editing]
RUN apt-get install -y ffmpeg


# Install Firefox and required dependencies for Selenium
RUN echo "deb http://deb.debian.org/debian/ unstable main contrib non-free" >> /etc/apt/sources.list.d/debian.list \
&& apt-get update \
&& apt-get install -y --no-install-recommends firefox


#Clean cache
RUN apt-get clean && \
rm -rf /var/lib/apt/lists/*

# Run main.py automatically when the container launches
#CMD ["python", "main.py"]

# Run bash when the container launches[for debugging so that we can run the script manually]
CMD ["bash"]