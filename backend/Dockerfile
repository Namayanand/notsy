# Build stage
FROM maven:3.9-eclipse-temurin-17 AS builder

WORKDIR /app

# Copy pom.xml first for dependency caching
COPY pom.xml .
RUN mvn dependency:go-offline -B

# Copy source code and build
COPY src ./src
RUN mvn clean package -DskipTests -B

# Runtime stage
FROM eclipse-temurin:17-jre

WORKDIR /app

# Create uploads directory
RUN mkdir -p /app/uploads

# Copy the built jar
COPY --from=builder /app/target/*.jar app.jar

# PORT is injected by Railway at runtime; default to 8080 for local Docker usage.
ENV PORT=8080
ENV JAVA_OPTS="-Xmx512m -Xms256m"

EXPOSE ${PORT}

# Pass $PORT to Spring Boot via server.port
ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -Dserver.port=$PORT -jar app.jar"]
