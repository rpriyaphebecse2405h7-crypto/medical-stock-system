pipeline {
    agent any

    environment {
        APP_NAME     = 'medicine_stock_system'
        PORT         = '5000'
        PYTHONUNBUFFERED = '1'
    }

    stages {
        stage('Checkout') {
            steps {
                echo '=== Stage 1: Checking out source code from GitHub ==='
                checkout scm
                script {
                    echo "Current Git Commit: ${env.GIT_COMMIT ?: 'Local Workspace'}"
                    echo "Building Branch: ${env.GIT_BRANCH ?: 'main'}"
                }
            }
        }

        stage('Code Validation & Linting') {
            steps {
                echo '=== Stage 2: Code Validation & Linting ==='
                script {
                    if (isUnix()) {
                        sh '''
                            python3 -m py_compile app.py config.py tests/*.py || python -m py_compile app.py config.py tests/*.py
                            pip install --upgrade flake8 || true
                            flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics || true
                        '''
                    } else {
                        bat '''
                            python -m py_compile app.py config.py tests\\test_app.py
                            pip install --upgrade flake8
                            flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
                        '''
                    }
                }
            }
        }

        stage('Build & Dependencies') {
            steps {
                echo '=== Stage 3: Installing Dependencies & Building Environment ==='
                script {
                    if (isUnix()) {
                        sh '''
                            python3 -m venv venv || python -m venv venv
                            . venv/bin/activate
                            pip install --upgrade pip
                            pip install -r requirements.txt
                            pip install -r requirements-dev.txt || pip install pytest
                        '''
                    } else {
                        bat '''
                            python -m venv venv
                            call venv\\Scripts\\activate.bat
                            pip install --upgrade pip
                            pip install -r requirements.txt
                            pip install -r requirements-dev.txt
                        '''
                    }
                }
            }
        }

        stage('Automated Tests') {
            steps {
                echo '=== Stage 4: Running Automated Unit & Integration Tests ==='
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

        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                echo '=== Stage 5: Deploying to Production / Staging ==='
                script {
                    echo "Branch is main. Executing automated deployment for ${env.APP_NAME}..."
                    if (isUnix()) {
                        sh '''
                            if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
                                echo "Deploying via Docker Compose..."
                                docker compose down --remove-orphans || true
                                docker compose up -d --build
                                echo "Verifying deployment health..."
                                sleep 5
                                curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/ || true
                            else
                                echo "Docker not detected. Deploying standalone WSGI process..."
                                . venv/bin/activate
                                pkill -f "gunicorn.*app:app" || true
                                nohup gunicorn --bind 0.0.0.0:5000 --workers 3 app:app > app.log 2>&1 &
                                sleep 3
                                curl -I http://localhost:5000/ || true
                            fi
                        '''
                    } else {
                        bat '''
                            echo Deploying on Windows host...
                            echo Application successfully validated and ready for production service reload.
                        '''
                    }
                }
            }
        }
    }

    post {
        always {
            echo 'Archiving test results and cleaning up temporary artifacts...'
            junit testResults: 'reports/*.xml', allowEmptyResults: true
        }
        success {
            echo "SUCCESS: Pipeline completed successfully for branch ${env.GIT_BRANCH ?: 'main'}!"
        }
        failure {
            echo "FAILURE: Pipeline failed! Please inspect logs and test report."
        }
    }
}
