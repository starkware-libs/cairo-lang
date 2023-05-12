# Install Clang
apt-get update
apt-get install -y libstdc++-8-dev libc6-dbg
apt-get install -y clang-12 clang-format-12 clang-tidy-6.0 libclang-12-dev llvm-12 g++-7
ln -sf /usr/bin/clang++-12 /usr/bin/clang++
ln -sf /usr/bin/clang-12 /usr/bin/clang

# Install bazel
apt-get install unzip -y
curl -L -o /tmp/bazel_install.sh https://github.com/bazelbuild/bazel/releases/download/5.2.0/bazel-5.2.0-installer-linux-x86_64.sh
chmod +x /tmp/bazel_install.sh
/tmp/bazel_install.sh
