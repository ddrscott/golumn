# Sorry I'm a Ruby guy

require 'fileutils'

desc 'Build App icon'
task :icon do
  # Your code goes here
  sh 'img2py -a -F -i -n AppIcon res/grid-128.ico golumn/images.py'
end

desc "Build and Release wheel"
task :release do
  version = File.read('golumn/__init__.py')[/__version__.*'(\d+\.\d+\.\d+)'/, 1]
  sh 'python2 setup.py bdist_wheel'
  sh "twine upload dist/golumn-#{version}-py2-none-any.whl"
end

desc "Build Mac App"
task :app do
  sh 'python2 setup-app.py py2app'
end
