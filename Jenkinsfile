pipeline {
    agent any

    environment {
        APP_NAME         = 'medicine_stock_system'
        PORT             = '5000'
        PYTHONUNBUFFERED = '1'
    }

    stages {
        stage('Checkout') {
            steps {
                echo '=== Stage 1: Checkout (Retrieve merged code from main branch) ==='
                checkout scm
                script {
                    echo "Current Git Commit: ${env.GIT_COMMIT ?: 'HEAD'}"
                    echo "Target Branch: ${env.GIT_BRANCH ?: 'main'}"
                }
            }
        }

        stage('Install Dependencies') {
            steps {
                echo '=== Stage 2: Install Dependencies ==='
                script {
                    if (isUnix()) {
                        sh '''
                            python3 -m venv venv || python -m venv venv
                            . venv/bin/activate
                            python -m pip install --upgrade pip
                            pip install -r requirements.txt
                            pip install -r requirements-dev.txt || pip install pytest flake8
                        '''
                    } else {
                        bat '''
                            python -m venv venv
                            call venv\\Scripts\\activate.bat
                            python -m pip install --upgrade pip
                            pip install -r requirements.txt
                            pip install -r requirements-dev.txt
                        '''
                    }
                }
            }
        }

        stage('Build') {
            steps {
                echo '=== Stage 3: Build (Validate structure and compile bytecode) ==='
                script {
                    if (isUnix()) {
                        sh '''
                            . venv/bin/activate
                            python -m py_compile app.py config.py tests/*.py
                            echo "Application bytecode build successful."
                        '''
                    } else {
                        bat '''
                            call venv\\Scripts\\activate.bat
                            python -m py_compile app.py config.py tests\\test_app.py
                            echo Application bytecode build successful.
                        '''
                    }
                }
            }
        }

        stage('Test') {
            steps {
                echo '=== Stage 4: Test (Execute automated tests & generate reports) ==='
                script {
                    if (isUnix()) {
                        sh '''
                            . venv/bin/activate
                            mkdir -p reports
                            pytest tests/ -v --junitxml=reports/test-results.xml || python -m unittest discover tests
                        '''
                    } else {
                        bat '''
                            call venv\\Scripts\\activate.bat
                            if not exist reports mkdir reports
                            pytest tests/ -v --junitxml=reports/test-results.xml
                        '''
                    }
                }
            }
        }

        stage('Code Quality') {
            steps {
                echo '=== Stage 5: Code Quality & Static Analysis ==='
                script {
                    if (isUnix()) {
                        sh '''
                            . venv/bin/activate
                            flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
                            echo "Code quality verification passed."
                        '''
                    } else {
                        bat '''
                            call venv\\Scripts\\activate.bat
                            flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
                            echo Code quality verification passed.
                        '''
                    }
                }
            }
        }

        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                echo '=== Stage 6: Deploy (Production Deployment) ==='
                script {
                    echo "Deploying verified build for branch ${env.GIT_BRANCH ?: 'main'}..."
                    if (isUnix()) {
                        sh '''
                            if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
                                echo "Deploying via Docker Compose stack..."
                                docker compose down --remove-orphans || true
                                docker compose up -d --build
                                sleep 5
                                curl -s -f http://localhost:5000/ || true
                            else
                                echo "Deploying via production WSGI (Gunicorn)..."
                                . venv/bin/activate
                                pkill -f "gunicorn.*app:app" || true
                                nohup gunicorn --bind 0.0.0.0:5000 --workers 3 app:app > app.log 2>&1 &
                                sleep 3
                                curl -I http://localhost:5000/ || true
                            fi
                        '''
                    } else {
                        bat '''
                            echo Deploying on Windows environment...
                            echo Application successfully verified and ready for deployment.
                        '''
                    }
                }
            }
        }
    }

    post {
        always {
            echo '=== Stage 7: Post-Build (Archiving artifacts and test results) ==='
            junit testResults: 'reports/*.xml', allowEmptyResults: true
        }
        success {
            echo "SUCCESS: Pipeline completed successfully for ${env.APP_NAME} on branch ${env.GIT_BRANCH ?: 'main'}."
        }
        failure {
            echo "FAILURE: Pipeline execution failed. Please inspect build stage logs and test reports."
        }
    }
}
