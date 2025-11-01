import { createRoute } from '@tanstack/react-router'
import type { RootRoute } from '@tanstack/react-router'
import { z } from 'zod'
import { createFormHook } from '@tanstack/react-form'
import { fieldContext, formContext } from '../hooks/demo.form-context'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { LoginForm } from '@/components/login-form'

const PASSWORD_MIN_SIZE = 6;
const schema = z.object({
  email: z.email(),
  password: z.string().min(PASSWORD_MIN_SIZE, `Atleast ${PASSWORD_MIN_SIZE} characters`),
});


export const { useAppForm } = createFormHook({
  fieldComponents: {
    TextField: Input,
  },
  formComponents: {
    Submit: Button,
  },
  fieldContext,
  formContext,
})

function Login() {
  const form = useAppForm({
    defaultValues: {
      email: '',
      password: '',
    },
    validators: {
      onBlur: schema,
    },
    onSubmit: ({ value }) => {
      console.log(value)
      // Show success message
      alert('Form submitted successfully!')
    },
  })
  return <div className="flex flex-col md:flex-row">
    <div className="w-full md:w-1/2 p-4 h-screen flex flex-col justify-center items-center">
      <LoginForm
        className="w-full max-w-[20rem]"
        email={
          <form.AppField name="email">
            {(field) => <field.TextField placeholder="johndoe@email.com" required />}
          </form.AppField>
        }
        password={
          <form.AppField name="password">
            {(field) => <field.TextField placeholder="A very good password" required />}
          </form.AppField>
        }
        submitButton={
          <form.AppForm>
            <form.Submit type="submit">Login</form.Submit>
          </form.AppForm>
        }
        onSubmit={(e) => {
          e.preventDefault()
          e.stopPropagation()
          form.handleSubmit()
        }}
        forgotPasswordLink='/forgot-password'
      />
    </div>
    <div className="hidden md:block sm:w-1/2 h-screen flex flex-col justify-center p-4 bg-[#efefef]">
    </div>
  </div>
}

export default (parentRoute: RootRoute) =>
  createRoute({
    path: '/login',
    component: Login,
    getParentRoute: () => parentRoute,
  })
