# Sorry I'm a Ruby guy

require 'fileutils'

desc 'Build App icon'
task :icon do
  # Your code goes here
  sh 'img2py -a -F -i -n AppIcon res/grid-128.ico golumn/images.py'
end

task :release do
  version = File.read('golumn/__init__.py')[/__version__.*'(\d+\.\d+\.\d+)'/, 1]
  sh 'python setup.py bdist_wheel'
  sh "twine upload dist/golumn-#{version}-py2-none-any.whl"
end
