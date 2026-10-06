# hope-runtime with the house programs, built from the sibling repos (build context: the parent directory).
# Stage 1: the Hope compiler (Kotlin).            Stage 2: the house programs compiled to .hbc.
# Stage 3: the VM and hope-runtime (C++).          Final: only the runtime binary and the programs.
FROM eclipse-temurin:21-jdk AS compiler
WORKDIR /src/compiler
COPY compiler/ ./
RUN chmod +x gradlew && ./gradlew --no-daemon -q installDist

FROM eclipse-temurin:21-jdk AS programs
COPY --from=compiler /src/compiler/build/install /opt/hopec
COPY houses/programs/ /programs/
RUN mkdir /hbc && for f in /programs/*.hope; do \
      /opt/hopec/*/bin/* --compile "$f" "/hbc/$(basename "$f" .hope).hbc"; \
    done && ls /hbc

FROM debian:bookworm-slim AS vm
RUN apt-get update && apt-get install -y --no-install-recommends g++ cmake make && rm -rf /var/lib/apt/lists/*
WORKDIR /src/vm
COPY vm/CMakeLists.txt ./
COPY vm/src/ src/
COPY vm/tests/ tests/
RUN cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j && ctest --test-dir build --output-on-failure

FROM debian:bookworm-slim
COPY --from=vm /src/vm/build/hope-runtime /usr/local/bin/
COPY --from=programs /hbc/ /hbc/
ENTRYPOINT ["hope-runtime"]
