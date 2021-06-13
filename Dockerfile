FROM ubuntu:18.04

RUN apt update
RUN apt install -y cmake python3.7 libgmp3-dev g++ python3-pip python3.7-dev python3.7-venv npm

COPY . /app/

# Build.
WORKDIR /app/
RUN ./build.sh

WORKDIR /app/build/Release
RUN make all -j8

# Run tests.
RUN ctest -V

WORKDIR /app/
RUN src/starkware/cairo/lang/package_test/run_test.sh

# Build the Visual Studio Code extension.
WORKDIR /app/src/starkware/cairo/lang/ide/vscode-cairo
RUN npm install -g vsce@1.87.1
RUN npm install
RUN vsce package

WORKDIR /app/
