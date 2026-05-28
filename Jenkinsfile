pipeline {
    agent any

    environment {
        APP_NAME        = "flask-books-api"
        DOCKER_IMAGE    = "${APP_NAME}"
        DOCKER_TAG      = "${BUILD_NUMBER}"
        STAGING_PORT    = "5001"
        PROD_PORT       = "5000"
        SONAR_TOKEN = credentials('SONAR_TOKEN')
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                echo "✅ Source checked out — build #${BUILD_NUMBER}"
            }
        }
        stage('Build') {
            steps {
                script {
                    echo " Building Docker image ${DOCKER_IMAGE}:${DOCKER_TAG}"
                    sh """
                        docker build \
                            --build-arg BUILD_NUMBER=${BUILD_NUMBER} \
                            -t ${DOCKER_IMAGE}:${DOCKER_TAG} \
                            -t ${DOCKER_IMAGE}:latest \
                            .
                    """
                    echo "✅ Image built: ${DOCKER_IMAGE}:${DOCKER_TAG}"
                }
            }
            post {
                success {
                    sh "docker inspect ${DOCKER_IMAGE}:${DOCKER_TAG} --format='{{.Id}}' > image-digest.txt"
                    archiveArtifacts artifacts: 'image-digest.txt', fingerprint: true
                }
            }
        }
        stage('Test') {
            steps {
                script {
                    echo " Running unit tests"
                    sh """
                        docker run --rm \
                            -v \$(pwd):/app \
                            -w /app \
                            ${DOCKER_IMAGE}:${DOCKER_TAG} \
                            sh -c "pip install pytest pytest-cov --quiet && \
                                   pytest test_app.py \
                                       --junitxml=test-results.xml \
                                       --cov=app \
                                       --cov-report=xml:coverage.xml \
                                       -v"
                    """
                }
            }
            post {
                always {
                    junit 'test-results.xml'
                }
                success {
                    echo "✅ All tests passed"
                    archiveArtifacts artifacts: 'coverage.xml', fingerprint: true
                }
                failure {
                    error "❌ Tests failed — aborting pipeline"
                }
            }
        }
        stage('SonarCloud Analysis') {
            steps {
                sh '''
                    curl -sSLo sonar-scanner.zip \
                        https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-5.0.1.3006-linux.zip

                    unzip -o sonar-scanner.zip

                    ./sonar-scanner-5.0.1.3006-linux/bin/sonar-scanner \
                        -Dsonar.token=${SONAR_TOKEN}
                '''
               
            }
            
        }

        stage('Security') {
            steps {
                script {
                    echo " Running Trivy security scan"
                    sh """
                        docker pull aquasec/trivy:latest
                        # LOW/MEDIUM — informational table
                        docker run --rm \
                            -v /var/run/docker.sock:/var/run/docker.sock \
                            -v trivy-cache:/root/.cache \
                            aquasec/trivy:latest image \
                                --exit-code 0 \
                                --severity LOW,MEDIUM \
                                --format table \
                                ${DOCKER_IMAGE}:${DOCKER_TAG}

                        # HIGH/CRITICAL — JSON report for archiving
                        docker run --rm \
                            -v /var/run/docker.sock:/var/run/docker.sock \
                            -v trivy-cache:/root/.cache \
                            -v \$(pwd):/output \
                            aquasec/trivy:latest image \
                                --exit-code 0 \
                                --severity HIGH,CRITICAL \
                                --format json \
                                --output /output/trivy-report.json \
                                ${DOCKER_IMAGE}:${DOCKER_TAG}
                    """
                    sh """
                        if [ -f trivy-report.json ]; then
                            COUNT=\$(python3 -c \
                                "import sys,json; d=json.load(open('trivy-report.json')); \
                                 v=[x for r in d.get('Results',[]) for x in r.get('Vulnerabilities',[]) or [] if x.get('Severity') in ['HIGH','CRITICAL']]; \
                                 print(len(v))")
                            echo "HIGH/CRITICAL CVEs found: \$COUNT"
                        fi
                    """
                }
            }
            post {
                always {
                    archiveArtifacts artifacts: 'trivy-report.json', allowEmptyArchive: true
                }
            }
        }

        stage('Deploy to Staging') {
            steps {
                script {
                    echo " Deploying to staging on port ${STAGING_PORT}"
                    sh """
                        docker rm -f ${APP_NAME}-staging 2>/dev/null || true

                        docker run -d \
                            --name ${APP_NAME}-staging \
                            -p ${STAGING_PORT}:5000 \
                            --restart unless-stopped \
                            -e FLASK_ENV=staging \
                            ${DOCKER_IMAGE}:${DOCKER_TAG}

                        sleep 5

                        curl -sf http://localhost:${STAGING_PORT}/api/books \
                            && echo "✅ Staging health check passed" \
                            || (echo "❌ Staging health check FAILED" )
                    """
                }
            }
        }
        stage('Release') {
            environment {
                RELEASE_TAG = "v1.${BUILD_NUMBER}"
            }
            steps {
                script {
                    echo "Releasing ${DOCKER_IMAGE}:${RELEASE_TAG}"
                    sh '''
                        docker tag $DOCKER_IMAGE:$DOCKER_TAG $DOCKER_IMAGE:$RELEASE_TAG
                        echo "✅ Docker image tagged: $DOCKER_IMAGE:$RELEASE_TAG"
                    '''
                    withCredentials([usernamePassword(
                        credentialsId: 'github-pat',         
                        usernameVariable: 'GIT_USERNAME',
                        passwordVariable: 'GIT_TOKEN'
                    )]) {
                        sh '''
                            git config user.email "jenkins@ci.local"
                            git config user.name  "Jenkins"
 
                            
                            git tag -fa $RELEASE_TAG \
                                -m "Release $RELEASE_TAG [build $BUILD_NUMBER]"
 
                            git remote set-url origin \
                                https://$GIT_USERNAME:$GIT_TOKEN@github.com/spaul-12/7.3HD.git
 
                            git push origin $RELEASE_TAG
 
                            git remote set-url origin \
                                https://github.com/spaul-12/7.3HD.git
 
                            echo "✅ Git tag $RELEASE_TAG pushed to GitHub"
                        '''
                    }
 
                    sh '''
                        docker rm -f $APP_NAME-prod 2>/dev/null || true
 
                        docker run -d \
                            --name $APP_NAME-prod \
                            -p $PROD_PORT:5000 \
                            --restart unless-stopped \
                            -e FLASK_ENV=production \
                            $DOCKER_IMAGE:$RELEASE_TAG
 
                        sleep 20

                    '''
                }
            }
            post {
                success {
                    echo "✅ Release ${RELEASE_TAG} deployed to production successfully"
                }
                failure {
                    echo "❌ Release ${RELEASE_TAG} failed — production was NOT updated"
                }
            }
        }
        

        stage('Monitoring') {
            steps {
                script {
                    echo " Starting monitoring stack"
                    sh """
                        docker compose -f docker-compose.monitoring.yaml up -d

                        sleep 30

                        curl -sf http://localhost:9090/-/healthy \
                            && echo "✅ Prometheus healthy" \
                            || echo "⚠️  Prometheus not yet ready "

                        curl -sf http://localhost:3000/api/health \
                            && echo "✅ Grafana healthy" \
                            || echo "⚠️  Grafana not yet ready "
                    """
                }
            }
        }
    }
    
    post {
        success {
            echo """
            ════════════════════════════════════════
            ✅  PIPELINE SUCCEEDED — Build #${BUILD_NUMBER}
                Image   : ${DOCKER_IMAGE}:v1.${BUILD_NUMBER}
                Staging : http://localhost:${STAGING_PORT}/api/books
                Prod    : http://localhost:${PROD_PORT}/api/books
                Grafana : http://localhost:3000
            ════════════════════════════════════════
            """
        }
        failure {
            echo "❌ Pipeline FAILED at build #${BUILD_NUMBER}."
        }
        always {
            sh "docker image prune -f || true"
        }
    }
}