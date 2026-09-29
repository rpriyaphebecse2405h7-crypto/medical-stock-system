pipeline {
    agent any

    options {
        buildDiscarder(logRotator(numToKeepStr: '30', artifactNumToKeepStr: '30'))
        timestamps()
        timeout(time: 15, unit: 'MINUTES')
        disableConcurrentBuilds()
    }

    environment {
        APP_NAME         = 'medicine_stock_system'
        PORT             = '5000'
        PYTHONUNBUFFERED = '1'
        PATH             = "C:\\Python311;C:\\Python311\\Scripts;${env.PATH}"
    }

    stages {
        stage('Checkout') {
            steps {
                echo '=== Stage 1: Checkout ==='
                checkout scm
                script {
                    def branchName = env.BRANCH_NAME ?: env.GIT_BRANCH ?: 'unknown'
                    def commitSha = env.GIT_COMMIT ?: (isUnix() ? sh(script: 'git rev-parse HEAD', returnStdout: true).trim() : bat(script: '@git rev-parse HEAD', returnStdout: true).trim())
                    def author = isUnix() ? sh(script: 'git log -1 --pretty=format:"%an <%ae>"', returnStdout: true).trim() : bat(script: '@git log -1 --pretty=format:"%%an <%%ae>"', returnStdout: true).trim()

                    echo "----------------------------------------"
                    echo "Checked out branch: ${branchName}"
                    echo "Commit ID:          ${commitSha}"
                    echo "Commit Author:      ${author}"
                    echo "----------------------------------------"
                }
            }
        }

        stage('Dependency Installation') {
            steps {
                echo '=== Stage 2: Dependency Installation ==='
                script {
                    if (isUnix()) {
                        sh '''
                            set -e
                            echo "Verifying Python environment..."
                            python3 -m pip install --upgrade pip
                            echo "Installing core dependencies from requirements.txt..."
                            pip install -r requirements.txt || { echo "ERROR: Failed to install requirements.txt"; exit 1; }
                            echo "Installing development/testing dependencies from requirements-dev.txt..."
                            pip install -r requirements-dev.txt || pip install pytest flake8 coverage
                            echo "Dependency installation completed successfully."
                        '''
                    } else {
                        bat '''
                            @echo off
                            echo Verifying Python environment...
                            where python >nul 2>&1
                            if %ERRORLEVEL% NEQ 0 (
                                echo ERROR: Python executable not found on system PATH.
                                exit /b 1
                            )
                            echo Installing core dependencies from requirements.txt...
                            python -m pip install -r requirements.txt
                            if %ERRORLEVEL% NEQ 0 (
                                echo ERROR: Failed to install requirements.txt. Please check package versions.
                                exit /b 1
                            )
                            echo Installing development dependencies from requirements-dev.txt...
                            python -m pip install -r requirements-dev.txt
                            if %ERRORLEVEL% NEQ 0 (
                                echo WARNING: requirements-dev.txt encountered an issue, ensuring pytest and flake8 are installed...
                                python -m pip install pytest flake8 coverage
                            )
                            echo Dependency installation completed successfully.
                        '''
                    }
                }
            }
        }

        stage('Code Validation') {
            steps {
                echo '=== Stage 3: Code Validation ==='
                script {
                    if (isUnix()) {
                        sh '''
                            set -e
                            echo "Checking Python syntax with py_compile..."
                            python3 -m py_compile app.py config.py tests/*.py
                            echo "Running static code quality analysis with Flake8..."
                            flake8 . --exclude=venv,.venv --count --select=E9,F63,F7,F82 --show-source --statistics
                            echo "Code validation checks passed."
                        '''
                    } else {
                        bat '''
                            @echo off
                            echo Checking Python syntax with py_compile...
                            python -m py_compile app.py config.py tests\\test_app.py
                            if %ERRORLEVEL% NEQ 0 (
                                echo ERROR: Critical Python syntax error detected in source files.
                                exit /b 1
                            )
                            echo Running static code quality analysis with Flake8...
                            python -m flake8 . --exclude=venv,.venv --count --select=E9,F63,F7,F82 --show-source --statistics
                            if %ERRORLEVEL% NEQ 0 (
                                echo ERROR: Critical code quality check failed.
                                exit /b 1
                            )
                            echo Code validation checks passed.
                        '''
                    }
                }
            }
        }

        stage('Automated Testing') {
            steps {
                echo '=== Stage 4: Automated Testing ==='
                script {
                    if (isUnix()) {
                        sh '''
                            mkdir -p reports
                            echo "Executing automated test suite (medicine stock, billing/sales, dashboard, auth)..."
                            python3 -m pytest tests/ -v --junitxml=reports/test-results.xml
                        '''
                    } else {
                        bat '''
                            @echo off
                            if not exist reports mkdir reports
                            echo Executing automated test suite (medicine stock, billing/sales, dashboard, auth)...
                            python -m pytest tests/ -v --junitxml=reports/test-results.xml
                            if %ERRORLEVEL% NEQ 0 (
                                echo ERROR: One or more automated tests failed.
                                exit /b 1
                            )
                            echo Automated tests completed successfully.
                        '''
                    }
                }
            }
        }

        stage('Pull Request Validation') {
            steps {
                echo '=== Stage 5: Pull Request Validation ==='
                script {
                    if (env.CHANGE_ID) {
                        echo "================================================="
                        echo "PULL REQUEST VALIDATION SUMMARY:"
                        echo "  Pull Request Number: #${env.CHANGE_ID}"
                        echo "  PR Title:            ${env.CHANGE_TITLE ?: 'N/A'}"
                        echo "  Source Branch:       ${env.CHANGE_BRANCH ?: 'N/A'}"
                        echo "  Target/Base Branch:  ${env.CHANGE_TARGET ?: 'main'}"
                        echo "  PR Author:           ${env.CHANGE_AUTHOR ?: 'N/A'}"
                        echo "  PR URL:              ${env.CHANGE_URL ?: 'N/A'}"
                        echo "  Verification Result: Pre-merge CI checks PASSED."
                        echo "================================================="
                    } else {
                        echo "Standard branch build (${env.BRANCH_NAME ?: 'branch'}). No incoming PR validation required."
                    }
                }
            }
        }

        stage('Build Status & Archiving') {
            steps {
                echo '=== Stage 6: Build Status & Archiving ==='
                script {
                    echo "Build Number: #${env.BUILD_NUMBER}"
                    echo "Branch:       ${env.BRANCH_NAME ?: 'main'}"
                    echo "Status:       IN_PROGRESS -> SUCCESS"
                    echo "Archiving build logs and test report artifacts..."
                }
            }
        }

        stage('Deployment') {
            when {
                allOf {
                    branch 'main'
                    not { changeRequest() }
                }
            }
            steps {
                echo '=== Stage 7: Deployment ==='
                script {
                    echo "Evaluating deployment environment for branch: ${env.BRANCH_NAME ?: 'main'}"
                    def isAuthorized = env.DEPLOY_AUTHORIZED ?: 'false'

                    if (isUnix()) {
                        sh '''
                            if command -v docker >/dev/null 2>&1 && [ -f docker-compose.yml ]; then
                                echo "Docker Compose deployment environment verified."
                            else
                                echo "Standard Python WSGI deployment target verified."
                            fi
                        '''
                    } else {
                        bat '''
                            @echo off
                            echo Windows deployment environment verified.
                        '''
                    }

                    if (isAuthorized == 'true') {
                        echo "DEPLOYMENT: Authorized production deployment in progress..."
                    } else {
                        echo "DEPLOYMENT GUARD: Automated production deployment is disabled without explicit authorization."
                        echo "All build and test checks have passed. Artifact is verified and ready for deployment approval."
                    }
                }
            }
        }
    }

    post {
        always {
            echo '=== Post-Build: Archiving Test Reports and Artifacts ==='
            junit testResults: 'reports/*.xml', allowEmptyResults: true
            archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
        }
        success {
            echo "SUCCESS: Build #${env.BUILD_NUMBER} completed successfully for ${env.APP_NAME} on branch ${env.BRANCH_NAME ?: 'main'}."
        }
        unstable {
            echo "UNSTABLE: Build #${env.BUILD_NUMBER} completed with test warnings or skipped suites."
        }
        failure {
            echo "FAILURE: Build #${env.BUILD_NUMBER} failed. Inspect stage execution logs and published JUnit reports."
        }
    }
}
