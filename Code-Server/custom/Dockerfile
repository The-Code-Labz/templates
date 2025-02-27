# Use the specified base image
FROM codercom/code-server:4.97.2-39

# Set the user to root
USER root


# Set the environment variable for non-interactive apt
ENV DEBIAN_FRONTEND=noninteractive

# Update and install prerequisites
RUN apt-get update && \
    apt-get install -y --no-install-recommends apt-transport-https ca-certificates curl gnupg2 || { echo "Failed to install prerequisites"; exit 1; }

# Add Docker's official GPG key
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | apt-key add - || { echo "Failed to add Docker GPG key"; exit 1; }

# Add Docker repository
RUN echo "deb [arch=amd64] https://download.docker.com/linux/debian $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list || { echo "Failed to add Docker repository"; exit 1; }

# Update package list again
RUN apt-get update || { echo "Failed to update package lists"; exit 1; }

# Install Docker and Docker Compose
RUN apt-get install -y docker.io docker-compose || { echo "Failed to install Docker"; exit 1; }

# Clean up
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

# Expose the port that code-server runs on
EXPOSE 3000

# Start the code-server
CMD ["code-server"]