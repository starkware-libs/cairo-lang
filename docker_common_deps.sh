curl -L -o /tmp/bazel_install.sh https://github.com/bazelbuild/bazel/releases/download/5.4.0/bazel-5.4.0-installer-linux-x86_64.sh
chmod +x /tmp/bazel_install.sh
/tmp/bazel_install.sh

groupadd -g 1234 starkware && useradd -m starkware -u 1234 -g 1234
