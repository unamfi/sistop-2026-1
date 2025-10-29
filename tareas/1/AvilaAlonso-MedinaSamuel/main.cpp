#include <iostream>
#include <queue>
#include <random>
#include <thread>
#include <mutex>
#include <condition_variable>

const int total_students = 10; // Total de estudiantes que se usarán para probar el programa
const int max_students = 4; // Máximos estudiantes permitidos al mismo tiempo
const int min_questions = 1; // Cada estudiante debe hacer al menos una pregunta
const int max_questions = 5; // El límite de preguntas por estudiante

std::mutex mtx;
std::condition_variable cv;
std::queue<std::pair<int, int>> questions;
bool running = true;


int current_students = 0;
std::vector<int> total_questions(total_students + 1);

int generate_random_int(int min, int max) {
  static std::random_device rd;
  static std::mt19937 gen(rd());

  std::uniform_int_distribution<> dist(min, max);
  return dist(gen);
}

void ask(int student_num) {
  printf("Entra el estudiante %d\n", student_num);
  for (int i = 1; i <= total_questions[student_num]; i++) {
    std::this_thread::sleep_for(std::chrono::milliseconds(generate_random_int(1000, 3000)));
    questions.emplace(student_num, i);
    cv.notify_one();
  }
}

void answer() {
  std::unique_lock<std::mutex> lock(mtx);
  while (running) {
    cv.wait(lock, [] { return !questions.empty(); });
    int student_num = questions.front().first, question_num = questions.front().second;
    printf("El profesor atiende la duda #%d del estudiante %d\n", question_num, student_num);
    questions.pop();

    if (question_num == total_questions[student_num]) {
      printf("Sale el estudiante %d\n", student_num);
      current_students--;
    }
  }
}

void sleep() {
  while (running) {
    if (current_students == 0) printf("El profesor esta durmiendo...\n");
    std::this_thread::sleep_for(std::chrono::milliseconds(1000));
  }
}

void generate_students() {
  int students_counter = total_students;
  size_t student_ind = 1;

  std::this_thread::sleep_for(std::chrono::seconds(2));

  while (students_counter--) {
    if (current_students < max_students) {
      current_students++;
      total_questions[student_ind] = generate_random_int(1, 5);
      std::thread new_student(ask, student_ind++);
      new_student.detach();
    }
    
    std::this_thread::sleep_for(std::chrono::seconds(generate_random_int(4, 6)));
  }

  running = false;
}

int main() {
  std::thread status(sleep);
  std::thread professor(answer);
  std::thread timer(generate_students);

  professor.join();
  status.join();
  timer.join();

  return 0;
}