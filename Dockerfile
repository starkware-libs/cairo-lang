FROM ciimage/python:3.9
RUN sed -i -e 's|http://archive\.ubuntu\.com/ubuntu/|mirror://mirrors.ubuntu.com/mirrors.txt|' /etc/apt/sources.list

COPY ./docker_common_deps.sh /app/
WORKDIR /app/
RUN ./docker_common_deps.sh
RUN apt-get install -y git libgmp3-dev python3-pip python3.9-venv python3.9-dev npm

# Install solc and ganache
RUN curl https://binaries.soliditylang.org/linux-amd64/solc-linux-amd64-v0.6.12+commit.27d51765 -o /usr/local/bin/solc-0.6.12
RUN echo 'f6cb519b01dabc61cab4c184a3db11aa591d18151e362fcae850e42cffdfb09a /usr/local/bin/solc-0.6.12' | sha256sum --check
RUN chmod +x /usr/local/bin/solc-0.6.12
RUN npm install -g --unsafe-perm ganache@7.4.3

COPY . /app

# Build the cairo-lang package.
RUN bazel build //src/starkware/cairo/lang:create_cairo_lang_package_zip
RUN build/bazelbin/src/starkware/cairo/lang/create_cairo_lang_package_zip

# Build and test all the targets.
RUN bazel build //...
RUN bazel test //...

RUN src/starkware/cairo/lang/package_test/run_test.sh

# Build the Visual Studio Code extension.
WORKDIR /app/src/starkware/cairo/lang/ide/vscode-cairo
RUN npm install -g vsce@1.87.1
RUN npm install
RUN vsce package

WORKDIR /app/
