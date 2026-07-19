FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /src
COPY pom.xml .
RUN mvn -q -DskipTests dependency:go-offline
COPY src ./src
RUN mvn -q -DskipTests package

FROM eclipse-temurin:21-jre
RUN useradd --system --uid 10001 demo
WORKDIR /app
COPY --from=build /src/target/demo-service-0.1.0.jar /app/demo-service.jar
USER demo
ENTRYPOINT ["java", "-jar", "/app/demo-service.jar"]
